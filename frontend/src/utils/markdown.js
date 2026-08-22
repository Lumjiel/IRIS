import MarkdownIt from 'markdown-it';
import mk from 'markdown-it-katex';
import DOMPurify from 'dompurify';

const md = new MarkdownIt({ html: true, linkify: true, typographer: true });
md.use(mk);
md.renderer.rules.heading_open = (tokens, idx) => {
    const token = tokens[idx];
    const content = tokens[idx + 1].content;
    const id = content.replace(/[^\w一-鿿]/g, '-').toLowerCase();
    return `<${token.tag} id="${id}">`;
};

export const renderMarkdown = (text) => {
    if (!text) return '';
    let raw = text.replace(/\\\[/g, '$$$').replace(/\\\]/g, '$$$');
    raw = raw.replace(/\\\(/g, '$').replace(/\\\)/g, '$');
    // 报告内容拼接了网络搜索原文（html:true 允许内联标签），
    // 必须经 DOMPurify 消毒再进 v-html，防搜索摘要夹带恶意标记。保留 id 供 TOC scrollspy 使用。
    return DOMPurify.sanitize(md.render(raw), { ADD_ATTR: ['id'] });
};
