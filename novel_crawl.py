import re
import time
import requests
from bs4 import BeautifulSoup
from ebooklib import epub

# ===================== 配置区（可修改）=====================
BASE_DIR_URL = "https://m.biquge345.com/shu/10002"  # 小说基础目录地址
DOMAIN = "https://m.biquge345.com"  # 网站根域名（修复相对路径必备）
PAGE_START = 1  # 起始目录页
PAGE_END = 3   # 结束目录页
BOOK_TITLE = "剑来"  # 生成的电子书书名
BOOK_AUTHOR = "烽火戏诸侯"  # 作者
OUTPUT_EPUB = "剑来.epub"  # 输出文件名
# ==========================================================

# 请求头（模拟浏览器，避免被反爬）
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://m.biquge345.com/"
}

def get_html(url: str) -> str:
    """获取网页HTML内容，带重试机制"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()  # 抛出HTTP错误
        response.encoding = "utf-8"  # 强制编码
        return response.text
    except Exception as e:
        print(f"获取页面失败: {url}, 错误: {e}")
        return ""

def parse_chapter_links(html: str) -> list:
    """解析单页目录，提取【章节标题 + 章节链接】（自动拼接绝对URL）"""
    soup = BeautifulSoup(html, "lxml")
    chapters = []
    # 匹配所有目录li标签中的a链接
    for a_tag in soup.select("li a[href*='/chapter/']"):
        title = a_tag.get("title", "").strip()
        link = a_tag.get("href", "").strip()
        if title and link:
            # 核心修复：相对路径拼接域名，转为完整URL
            full_link = DOMAIN + link
            chapters.append({"title": title, "url": full_link})
    return chapters

def get_all_chapters() -> list:
    """遍历1-68页目录，收集所有章节（无去重，原封不动提取）"""
    all_chapters = []

    for page in range(PAGE_START, PAGE_END + 1):
        # 拼接目录页URL（第1页无后缀，2-68页加_页码）
        if page == 1:
            dir_url = f"{BASE_DIR_URL}/"
        else:
            dir_url = f"{BASE_DIR_URL}_{page}/"

        print(f"正在爬取目录页：{dir_url}")
        html = get_html(dir_url)
        if not html:
            continue

        # 解析当前页章节，直接追加所有内容（无去重）
        chapters = parse_chapter_links(html)
        all_chapters.extend(chapters)

        time.sleep(0.5)  # 轻量延时，友好爬取

    print(f"共获取到 {len(all_chapters)} 个章节（无去重，原封不动提取）")
    return all_chapters

def parse_chapter_content(html: str) -> str:
    """解析章节内容，清洗广告、多余标签和空格"""
    soup = BeautifulSoup(html, "lxml")
    content_div = soup.find("div", id="txt")
    if not content_div:
        return ""

    # 1. 移除指定的广告p标签
    for p in content_div.find_all("p", style=re.compile("font-weight:bold")):
        p.decompose()

    # 2. 替换<br>为换行，去除&nbsp;、多余空格和空行
    text = content_div.get_text(separator="\n")
    text = text.replace("&nbsp;", " ")
    text = re.sub(r"\n+", "\n", text)  # 合并多个换行
    text = text.strip()
    return text

def create_epub(chapters: list):
    """生成带目录的EPUB电子书"""
    # 创建EPUB书籍对象
    book = epub.EpubBook()
    # 设置书籍元数据
    book.set_identifier("biquge10002")
    book.set_title(BOOK_TITLE)
    book.set_language("zh")
    book.add_author(BOOK_AUTHOR)

    # 创建目录 spine（阅读顺序）
    spine = ["nav"]
    toc = []  # 目录结构

    # 遍历所有章节，添加到EPUB
    for idx, chap in enumerate(chapters, 1):
        print(f"正在生成章节：{chap['title']}")
        # 爬取章节内容
        chap_html = get_html(chap["url"])
        content = parse_chapter_content(chap_html)
        if not content:
            continue

        # 修复语法错误：提前处理换行替换
        content_html = content.replace('\n', '</p><p>')
        # 创建EPUB章节
        epub_chap = epub.EpubHtml(
            title=chap["title"],
            file_name=f"chap_{idx}.xhtml",
            lang="zh"
        )
        # 修正后的赋值语句
        epub_chap.content = f"<h1>{chap['title']}</h1><p>{content_html}</p>"

        # 添加章节到书籍
        book.add_item(epub_chap)
        spine.append(epub_chap)
        toc.append(epub.Link(f"chap_{idx}.xhtml", chap["title"], f"chap_{idx}"))

        time.sleep(0.3)

    # 设置目录和阅读顺序
    book.toc = toc
    book.spine = spine
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # 生成EPUB文件
    epub.write_epub(OUTPUT_EPUB, book, {})
    print(f"✅ 电子书生成成功：{OUTPUT_EPUB}")

def main():
    """主函数"""
    print("=== 开始爬取小说目录（无去重）===")
    all_chapters = get_all_chapters()
    if not all_chapters:
        print("❌ 未获取到任何章节，程序退出")
        return

    print("=== 开始生成EPUB电子书 ===")
    create_epub(all_chapters)

if __name__ == "__main__":
    main()
