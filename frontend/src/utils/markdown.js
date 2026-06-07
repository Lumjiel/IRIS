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

export const renderMarkdown = (text) => {
    if (!text) return '';
    let raw = text.replace(/\\\[/g, '$$$').replace(/\\\]/g, '$$$');
    raw = raw.replace(/\\\(/g, '$').replace(/\\\)/g, '$');
    return md.render(raw);
};
