import re
import time
import requests
from bs4 import BeautifulSoup
from ebooklib import epub

# ===================== 配置区（可修改）=====================
BASE_DIR_URL = "https://m.biquge345.com/shu/10002"  # 小说基础目录地址
DOMAIN = "https://m.biquge345.com"  # 网站根域名
PAGE_START = 1  # 起始目录页
PAGE_END = 68   # 结束目录页
BOOK_TITLE = "剑来"  # 电子书书名
BOOK_AUTHOR = "烽火戏诸侯"  # 作者
OUTPUT_EPUB = "剑来.epub"  # 输出文件名
# ==========================================================

# 请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://m.biquge345/"
}

def get_html(url: str) -> str:
    """获取网页HTML内容"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        response.encoding = "utf-8"
        return response.text
    except Exception as e:
        print(f"获取页面失败: {url}, 错误: {e}")
        return ""

def parse_chapter_links(html: str) -> list:
    """解析章节链接，自动转为完整URL"""
    soup = BeautifulSoup(html, "lxml")
    chapters = []
    for a_tag in soup.select("li a[href*='/chapter/']"):
        title = a_tag.get("title", "").strip()
        link = a_tag.get("href", "").strip()
        if title and link:
            full_link = DOMAIN + link
            chapters.append({"title": title, "url": full_link})
    return chapters

def get_all_chapters() -> list:
    """遍历1-68页目录，无去重提取所有章节"""
    all_chapters = []
    for page in range(PAGE_START, PAGE_END + 1):
        dir_url = f"{BASE_DIR_URL}/" if page == 1 else f"{BASE_DIR_URL}_{page}/"
        print(f"正在爬取目录页：{dir_url}")
        html = get_html(dir_url)
        if not html:
            continue
        chapters = parse_chapter_links(html)
        all_chapters.extend(chapters)
        time.sleep(0.5)
    print(f"共获取到 {len(all_chapters)} 个章节")
    return all_chapters

def parse_chapter_content(html: str) -> str:
    """清洗章节内容，去除广告"""
    soup = BeautifulSoup(html, "lxml")
    content_div = soup.find("div", id="txt")
    if not content_div:
        return ""
    # 移除广告
    for p in content_div.find_all("p", style=re.compile("font-weight:bold")):
        p.decompose()
    text = content_div.get_text(separator="\n")
    text = text.replace("&nbsp;", " ")
    text = re.sub(r"\n+", "\n", text).strip()
    return text

def create_epub(chapters: list):
    """生成EPUB（首行缩进2字+两端对齐）"""
    book = epub.EpubBook()
    # 书籍元数据
    book.set_identifier("biquge10002")
    book.set_title(BOOK_TITLE)
    book.set_language("zh")
    book.add_author(BOOK_AUTHOR)

    # ===================== 核心：自定义CSS样式 =====================
    # 首行缩进2个汉字 + 两端对齐 + 舒适行高
    custom_css = epub.EpubItem(
        uid="style_nav",
        file_name="style.css",
        media_type="text/css",
        content="""
        /* 段落样式：首行缩进2em(2字) + 两端对齐 + 行高1.6 */
        p {
            text-indent: 2em;
            text-align: justify;
            line-height: 1.6;
            margin: 0 0 0.5em 0;
        }
        /* 章节标题居中 */
        h1 {
            text-align: center;
            font-size: 1.5em;
            margin: 1em 0;
        }
        """
    )
    book.add_item(custom_css)
    # ==============================================================

    spine = ["nav"]
    toc = []

    for idx, chap in enumerate(chapters, 1):
        print(f"正在生成章节：{chap['title']}")
        chap_html = get_html(chap["url"])
        content = parse_chapter_content(chap_html)
        if not content:
            continue

        content_html = content.replace('\n', '</p><p>')
        epub_chap = epub.EpubHtml(
            title=chap["title"],
            file_name=f"chap_{idx}.xhtml",
            lang="zh"
        )
        # 绑定CSS样式
        epub_chap.add_item(custom_css)
        # 章节内容
        epub_chap.content = f"""
        <html>
            <head><link rel="stylesheet" href="style.css" /></head>
            <body>
                <h1>{chap['title']}</h1>
                <p>{content_html}</p>
            </body>
        </html>
        """

        book.add_item(epub_chap)
        spine.append(epub_chap)
        toc.append(epub.Link(f"chap_{idx}.xhtml", chap["title"], f"chap_{idx}"))
        time.sleep(0.3)

    # 目录配置
    book.toc = toc
    book.spine = spine
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # 生成文件
    epub.write_epub(OUTPUT_EPUB, book, {})
    print(f"✅ 电子书生成成功：{OUTPUT_EPUB}")

def main():
    print("=== 开始爬取小说目录（无去重）===")
    all_chapters = get_all_chapters()
    if not all_chapters:
        print("❌ 未获取到任何章节，程序退出")
        return
    print("=== 开始生成EPUB电子书 ===")
    create_epub(all_chapters)

if __name__ == "__main__":
    main()
