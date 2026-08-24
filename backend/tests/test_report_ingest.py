"""report_ingest.py 研报入库测试。

全部 mock，不依赖真实网络和文件系统。
"""
import pytest
from unittest.mock import patch, MagicMock
from app.rag.report_ingest import extract_report_metadata, ingest_report


class TestExtractReportMetadata:
    """研报元数据抽取测试。"""

    def test_extract_stock_code(self):
        """抽取 A 股代码"""
        text = "复星医药（600196）投资价值分析报告"
        meta = extract_report_metadata(text)
        assert meta["stock_code"] == "600196"

    def test_extract_rating(self):
        """抽取券商评级"""
        text = "我们给予复星医药（600196）买入评级"
        meta = extract_report_metadata(text)
        assert meta["rating"] == "买入"

    def test_extract_target_price(self):
        """抽取目标价"""
        text = "目标价：35.5元"
        meta = extract_report_metadata(text)
        assert meta["target_price"] == "35.5"

    def test_extract_date(self):
        """抽取日期"""
        text = "报告日期：2025-08-20"
        meta = extract_report_metadata(text)
        assert meta["report_date"] == "2025-08-20"

    def test_extract_company_name(self):
        """抽取公司名"""
        text = "复星医药股份有限公司是一家..."
        meta = extract_report_metadata(text)
        assert meta["stock_name"] == "复星医药股份"

    def test_extract_all_fields(self):
        """抽取全部字段"""
        text = """
        复星医药（600196）投资分析报告
        报告日期：2025年08月20日
        给予评级：买入
        目标价：35.5元
        """
        meta = extract_report_metadata(text, filename="test_report.pdf")
        assert meta["stock_code"] == "600196"
        assert meta["rating"] == "买入"
        assert meta["target_price"] == "35.5"
        assert meta["report_date"] == "2025-08-20"
        assert meta["source"] == "券商研报"
        assert meta["filename"] == "test_report.pdf"
        assert "ingest_time" in meta

    def test_no_match_returns_minimal_metadata(self):
        """无匹配时返回最简元数据"""
        text = "这是一段没有任何研报特征的文本"
        meta = extract_report_metadata(text)
        assert meta["source"] == "券商研报"
        assert "stock_code" not in meta
        assert "rating" not in meta


class TestIngestReport:
    """研报入库测试。"""

    @patch("app.rag.engine.embeddings")
    @patch("app.rag.report_ingest.os.path.exists", return_value=True)
    @patch("langchain_community.vectorstores.Chroma")
    @patch("app.rag.report_ingest.extract_text_from_pdf")
    def test_ingest_success(self, mock_extract, mock_chroma, mock_exists, mock_embeddings):
        """正常入库流程"""
        mock_extract.return_value = "复星医药（600196）投资分析报告\n买入评级\n目标价：35.5元"
        mock_vectorstore = MagicMock()
        mock_chroma.return_value = mock_vectorstore

        result = ingest_report("/fake/path/report.pdf", "report.pdf")

        assert result["success"] is True
        assert result["chunks"] > 0
        assert result["metadata"]["stock_code"] == "600196"
        assert result["metadata"]["rating"] == "买入"
        mock_vectorstore.add_documents.assert_called_once()

    def test_ingest_file_not_found(self):
        """文件不存在"""
        result = ingest_report("/nonexistent/report.pdf")
        assert result["success"] is False
        assert "文件不存在" in result["error"]

    @patch("app.rag.engine.embeddings")
    @patch("app.rag.report_ingest.os.path.exists", return_value=True)
    @patch("app.rag.report_ingest.extract_text_from_pdf")
    def test_ingest_empty_pdf(self, mock_extract, mock_exists, mock_embeddings):
        """PDF 文本为空"""
        mock_extract.return_value = "   "
        result = ingest_report("/fake/path/empty.pdf")
        assert result["success"] is False
        assert "PDF 文本为空" in result["error"]

    @patch("app.rag.engine.embeddings")
    @patch("app.rag.report_ingest.os.path.exists", return_value=True)
    @patch("app.rag.report_ingest.extract_text_from_pdf")
    def test_ingest_pdf_extraction_failure(self, mock_extract, mock_exists, mock_embeddings):
        """PDF 抽取失败"""
        mock_extract.side_effect = RuntimeError("PyMuPDF 未安装")
        result = ingest_report("/fake/path/report.pdf")
        assert result["success"] is False
        assert "PyMuPDF" in result["error"]


class TestSearchReports:
    """研报检索测试。"""

    @patch("app.rag.engine.embeddings")
    @patch("langchain_community.vectorstores.Chroma")
    def test_search_with_stock_code_filter(self, mock_chroma, mock_embeddings):
        """按股票代码过滤检索"""
        import asyncio
        from app.rag.report_ingest import search_reports
        mock_vectorstore = MagicMock()
        mock_chroma.return_value = mock_vectorstore
        mock_vectorstore.similarity_search_with_score.return_value = [
            (MagicMock(page_content="研报内容", metadata={"stock_code": "600196"}), 0.95)
        ]

        results = asyncio.run(search_reports("复星医药", stock_code="600196"))

        assert len(results) == 1
        # 候选数(1) <= top_k(5)，不触发 rerank，score 保持 Chroma distance 语义
        assert results[0]["reranked"] is False
        assert results[0]["score"] == 0.95
        assert results[0]["metadata"]["stock_code"] == "600196"
        mock_vectorstore.similarity_search_with_score.assert_called_once()

    @patch("app.rag.report_ingest.os.path.exists", return_value=False)
    def test_search_no_database(self, mock_exists):
        """数据库不存在时返回空"""
        import asyncio
        from app.rag.report_ingest import search_reports
        results = asyncio.run(search_reports("复星医药"))
        assert results == []
