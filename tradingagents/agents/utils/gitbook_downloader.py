import aiohttp
import asyncio
from bs4 import BeautifulSoup
import markdownify as md
from urllib.parse import urljoin, urlparse
from slugify import slugify as slugify_lib
import re
from typing import Dict, Optional, List
from tradingagents.utils.logging_manager import get_logger

logger = get_logger('agents.utils')

class GitbookDownloader:
    """
    一个独立的工具类，用于从GitBook或类似结构的文档网站下载内容并转换为Markdown。
    核心逻辑借鉴自 https://github.com/Amal-David/gitbook-downloader
    """
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.visited_urls = set()
        self.pages = {} # 使用字典来存储页面，键为索引
        self.content_hashes = set() # 用于检查重复内容
        self.session = None

    async def download(self) -> Optional[str]:
        """执行下载和转换的主函数"""
        logger.info(f"📚 [GitbookDownloader] 开始下载: {self.base_url}")
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            async with aiohttp.ClientSession(headers=headers) as self.session:
                initial_content = await self._fetch_page(self.base_url)
                if not initial_content:
                    logger.error(f"无法获取初始页面: {self.base_url}")
                    return None
                
                nav_links = self._extract_nav_links(initial_content)
                logger.debug(f"📚 [GitbookDownloader] 发现 {len(nav_links)} 个导航链接")
                
                all_urls = [self.base_url] + nav_links
                tasks = [self._process_url(url, index) for index, url in enumerate(all_urls)]
                await asyncio.gather(*tasks)
                
                return self._generate_markdown()
        except Exception as e:
            logger.error(f"📚 [GitbookDownloader] 下载过程中发生严重错误: {e}")
            return None

    async def _fetch_page(self, url: str, max_retries=3, retry_delay=2) -> Optional[str]:
        """异步获取页面内容，包含重试逻辑"""
        for attempt in range(max_retries):
            try:
                # 尝试禁用SSL验证来绕过SSLError
                async with self.session.get(url, timeout=30, ssl=False) as response:
                    if response.status == 200:
                        return await response.text()
                    logger.warning(f"请求失败，状态码: {response.status}, URL: {url}")
            except Exception as e:
                logger.warning(f"获取页面时出错: {url}, 尝试次数 {attempt + 1}/{max_retries}, 错误: {e}")
            
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay * (2 ** attempt))
        return None

    def _extract_nav_links(self, html_content: str) -> List[str]:
        """从HTML中提取导航链接"""
        soup = BeautifulSoup(html_content, 'lxml')
        nav_links = []
        processed_urls = {self.base_url}

        for nav in soup.find_all(['nav', 'aside']):
            for link in nav.find_all('a', href=True):
                href = link['href']
                full_url = urljoin(self.base_url + '/', href.lstrip('/'))
                
                if full_url.startswith(self.base_url) and '#' not in full_url and full_url not in processed_urls:
                    nav_links.append(full_url)
                    processed_urls.add(full_url)
        
        return list(dict.fromkeys(nav_links))

    async def _process_url(self, url: str, index: int):
        """获取并处理单个URL"""
        if url in self.visited_urls:
            return
        self.visited_urls.add(url)
        
        content = await self._fetch_page(url)
        if not content:
            return
        
        soup = BeautifulSoup(content, 'lxml')
        
        title = soup.find('h1').get_text(strip=True) if soup.find('h1') else "Untitled"
        
        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile(r'(content|main|body|article)')) or soup.body
        
        if main_content:
            for tag in main_content.find_all(['nav', 'aside', 'header', 'footer', 'script', 'style']):
                tag.decompose()
            
            markdown_content = md.markdownify(str(main_content), heading_style="ATX").strip()
            content_hash = hash(markdown_content)
            
            if content_hash not in self.content_hashes:
                self.pages[index] = {'index': index, 'title': title, 'content': markdown_content, 'url': url}
                self.content_hashes.add(content_hash)
                logger.debug(f"✅ [GitbookDownloader] 已处理页面: {title} ({url})")

    def _generate_markdown(self) -> str:
        """根据已处理的页面生成完整的Markdown字符串"""
        if not self.pages:
            return "未能从文档网站提取任何内容。"
        
        sorted_pages = sorted(self.pages.values(), key=lambda x: x['index'])
        
        toc = ["# Table of Contents\n"]
        for page in sorted_pages:
            title = page['title']
            slug = slugify_lib(title)
            toc.append(f"- [{title}](#{slug})")
        
        content_parts = ["\n---\n"]
        for page in sorted_pages:
            content_parts.append(f"\n# {page['title']}")
            content_parts.append(f"\n_Source: <{page['url']}>_\n")
            content_parts.append(page['content'])
            content_parts.append("\n---\n")
            
        return "\n".join(toc) + "\n".join(content_parts)
