import MarkdownIt from 'markdown-it';
import mk from 'markdown-it-katex';

const md = new MarkdownIt({ html: true, linkify: true, typographer: true });
md.use(mk);

md.renderer.rules.heading_open = (tokens, idx) => {
    const token = tokens[idx];
    const content = tokens[idx + 1].content;
    const id = content.replace(/[^\w一-鿿]/g, '-').toLowerCase();
    return `<${token.tag} id="${id}">`;
};

// 代码块：加语言标签 + 复制按钮（借鉴 LobeChat/成熟聊天 UI 的代码块交互）
md.renderer.rules.fence = (tokens, idx, options, env, self) => {
    const token = tokens[idx];
    const info = (token.info || '').trim();
    const lang = info ? info.split(/\s+/)[0] : '';
    const content = md.utils.escapeHtml(token.content);
    return (
        `<div class="code-block">` +
        `<div class="code-block-header"><span class="code-block-lang">${lang || 'code'}</span>` +
        `<button class="code-block-copy" data-code="${encodeURIComponent(token.content)}" onclick="window.copyCodeBlock && window.copyCodeBlock(this)">复制</button></div>` +
        `<pre><code${lang ? ` class="language-${lang}"` : ''}>${content}</code></pre>` +
        `</div>`
    );
};

// 从参考文献区提取 [n] -> url 映射
function extractCitationMap(text) {
    const map = {};
    const re = /\[(\d+)\][^\n]*?—\s*(https?:\/\/[^\s\]]+)/g;
    let m;
    while ((m = re.exec(text))) map[m[1]] = m[2];
    return map;
}

export const renderMarkdown = (text) => {
    if (!text) return '';
    let raw = text.replace(/\\\[/g, '$$$').replace(/\\\]/g, '$$$');
    raw = raw.replace(/\\\(/g, '$').replace(/\\\)/g, '$');

    // 引用可点击跳转来源（深度调研工具特色）
    const citeMap = extractCitationMap(raw);
    if (Object.keys(citeMap).length > 0) {
        raw = raw.replace(/\[(\d+)\]/g, (match, n) => {
            if (citeMap[n]) return `<a class="citation-ref" href="${citeMap[n]}" target="_blank" rel="noopener">[${n}]</a>`;
            return match;
        });
    }
    return md.render(raw);
};

// 挂到 window，供 v-html 注入的复制按钮调用（事件委托之外的简单方案）
if (typeof window !== 'undefined') {
    window.copyCodeBlock = (btn) => {
        const code = btn.getAttribute('data-code');
        if (!code) return;
        try {
            const text = decodeURIComponent(code);
            navigator.clipboard.writeText(text).then(() => {
                const old = btn.textContent;
                btn.textContent = '已复制 ✓';
                setTimeout(() => { btn.textContent = old; }, 1500);
            });
        } catch { /* ignore */ }
    };
}