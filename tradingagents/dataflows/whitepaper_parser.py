"""
白皮书下载和解析工具
支持PDF下载、解析和内容提取
"""

import os
import re
import requests
import hashlib
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse
from pathlib import Path
import logging

# PDF处理库
try:
    import PyPDF2
    import pdfplumber
except ImportError:
    PyPDF2 = None
    pdfplumber = None

# 网页解析库
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

from tradingagents.utils.logging_init import get_logger

logger = get_logger("whitepaper_parser")


class WhitepaperParser:
    """白皮书解析器"""
    
    def __init__(self, cache_dir: str = "./cache/whitepapers"):
        """
        初始化白皮书解析器
        
        Args:
            cache_dir: 白皮书缓存目录
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 检查依赖
        self.pdf_available = PyPDF2 is not None and pdfplumber is not None
        self.html_available = BeautifulSoup is not None
        
        if not self.pdf_available:
            logger.warning("PDF处理库未安装，白皮书解析功能受限")
        if not self.html_available:
            logger.warning("HTML解析库未安装，网页内容解析功能受限")
    
    def download_whitepaper(self, url: str, coin_id: str) -> Optional[str]:
        """
        下载白皮书到本地缓存
        
        Args:
            url: 白皮书URL
            coin_id: 加密货币ID
            
        Returns:
            本地文件路径，如果下载失败返回None
        """
        try:
            # 生成文件名
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            file_extension = self._get_file_extension(url)
            filename = f"{coin_id}_{url_hash}{file_extension}"
            file_path = self.cache_dir / filename
            
            # 如果文件已存在，直接返回
            if file_path.exists():
                logger.info(f"白皮书已缓存: {file_path}")
                return str(file_path)
            
            # 下载文件
            logger.info(f"正在下载白皮书: {url}")
            response = requests.get(url, timeout=30, stream=True)
            response.raise_for_status()
            
            # 保存文件
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"白皮书下载完成: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"白皮书下载失败 {url}: {e}")
            return None
    
    def _get_file_extension(self, url: str) -> str:
        """获取文件扩展名"""
        parsed_url = urlparse(url)
        path = parsed_url.path.lower()
        
        if path.endswith('.pdf'):
            return '.pdf'
        elif path.endswith('.html') or path.endswith('.htm'):
            return '.html'
        else:
            return '.pdf'  # 默认假设是PDF
    
    def parse_pdf(self, file_path: str) -> Dict[str, any]:
        """
        解析PDF文件
        
        Args:
            file_path: PDF文件路径
            
        Returns:
            解析结果字典
        """
        if not self.pdf_available:
            return {"error": "PDF处理库未安装"}
        
        try:
            result = {
                "text": "",
                "pages": 0,
                "sections": {},
                "metadata": {}
            }
            
            # 使用pdfplumber解析（更准确）
            if pdfplumber:
                with pdfplumber.open(file_path) as pdf:
                    result["pages"] = len(pdf.pages)
                    
                    # 提取文本
                    text_parts = []
                    for page_num, page in enumerate(pdf.pages):
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(f"=== 第{page_num + 1}页 ===\n{page_text}")
                    
                    result["text"] = "\n\n".join(text_parts)
                    
                    # 提取元数据
                    if hasattr(pdf, 'metadata') and pdf.metadata:
                        result["metadata"] = {
                            "title": pdf.metadata.get("Title", ""),
                            "author": pdf.metadata.get("Author", ""),
                            "subject": pdf.metadata.get("Subject", ""),
                            "creator": pdf.metadata.get("Creator", ""),
                            "creation_date": str(pdf.metadata.get("CreationDate", "")),
                        }
            
            # 备用方案：使用PyPDF2
            elif PyPDF2:
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    result["pages"] = len(pdf_reader.pages)
                    
                    # 提取文本
                    text_parts = []
                    for page_num, page in enumerate(pdf_reader.pages):
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(f"=== 第{page_num + 1}页 ===\n{page_text}")
                    
                    result["text"] = "\n\n".join(text_parts)
                    
                    # 提取元数据
                    if pdf_reader.metadata:
                        result["metadata"] = {
                            "title": pdf_reader.metadata.get("/Title", ""),
                            "author": pdf_reader.metadata.get("/Author", ""),
                            "subject": pdf_reader.metadata.get("/Subject", ""),
                            "creator": pdf_reader.metadata.get("/Creator", ""),
                        }
            
            # 分析内容结构
            result["sections"] = self._analyze_whitepaper_structure(result["text"])
            
            return result
            
        except Exception as e:
            logger.error(f"PDF解析失败 {file_path}: {e}")
            return {"error": f"PDF解析失败: {e}"}
    
    def parse_html(self, file_path: str) -> Dict[str, any]:
        """
        解析HTML文件
        
        Args:
            file_path: HTML文件路径
            
        Returns:
            解析结果字典
        """
        if not self.html_available:
            return {"error": "HTML解析库未安装"}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # 提取文本内容
            text = soup.get_text(separator='\n', strip=True)
            
            # 提取标题
            titles = []
            for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                titles.extend([h.get_text().strip() for h in soup.find_all(tag)])
            
            # 提取链接
            links = []
            for link in soup.find_all('a', href=True):
                links.append({
                    "text": link.get_text().strip(),
                    "url": link['href']
                })
            
            return {
                "text": text,
                "titles": titles,
                "links": links,
                "sections": self._analyze_whitepaper_structure(text)
            }
            
        except Exception as e:
            logger.error(f"HTML解析失败 {file_path}: {e}")
            return {"error": f"HTML解析失败: {e}"}
    
    def _analyze_whitepaper_structure(self, text: str) -> Dict[str, List[str]]:
        """
        分析白皮书结构
        
        Args:
            text: 白皮书文本内容
            
        Returns:
            结构分析结果
        """
        sections = {
            "team_info": [],
            "tokenomics": [],
            "technology": [],
            "roadmap": [],
            "governance": [],
            "economics": [],
            "security": [],
            "use_cases": []
        }
        
        # 定义关键词模式
        patterns = {
            "team_info": [
                r"team", r"founder", r"developer", r"core team", r"advisors",
                r"leadership", r"creator", r"architect", r"co-founder"
            ],
            "tokenomics": [
                r"token", r"supply", r"circulating", r"total supply", r"max supply",
                r"inflation", r"deflation", r"distribution", r"allocation",
                r"vesting", r"burn", r"mint", r"economics", r"tokenomics"
            ],
            "technology": [
                r"consensus", r"blockchain", r"protocol", r"algorithm",
                r"cryptography", r"security", r"scalability", r"performance",
                r"architecture", r"implementation", r"technical"
            ],
            "roadmap": [
                r"roadmap", r"milestone", r"phase", r"upgrade", r"launch",
                r"release", r"development", r"timeline", r"schedule",
                r"future", r"plan", r"vision"
            ],
            "governance": [
                r"governance", r"voting", r"decision", r"proposal", r"community",
                r"dao", r"decentralized", r"autonomous", r"stakeholder"
            ],
            "economics": [
                r"economic", r"economy", r"financial", r"monetary", r"fiscal",
                r"incentive", r"reward", r"penalty", r"fee", r"cost"
            ],
            "security": [
                r"security", r"attack", r"vulnerability", r"risk", r"threat",
                r"protection", r"defense", r"audit", r"verification"
            ],
            "use_cases": [
                r"use case", r"application", r"scenario", r"example", r"usage",
                r"adoption", r"implementation", r"deployment"
            ]
        }
        
        # 按段落分析
        paragraphs = text.split('\n\n')
        
        for paragraph in paragraphs:
            paragraph_lower = paragraph.lower()
            
            for section, keywords in patterns.items():
                for keyword in keywords:
                    if re.search(keyword, paragraph_lower):
                        # 提取包含关键词的句子
                        sentences = paragraph.split('.')
                        relevant_sentences = [
                            s.strip() for s in sentences 
                            if keyword in s.lower() and len(s.strip()) > 20
                        ]
                        sections[section].extend(relevant_sentences[:2])  # 最多2句
                        break
        
        # 去重和清理
        for section in sections:
            sections[section] = list(set(sections[section]))[:5]  # 最多5条
        
        return sections
    
    def parse_whitepaper(self, url: str, coin_id: str) -> Dict[str, any]:
        """
        解析白皮书的完整流程
        
        Args:
            url: 白皮书URL
            coin_id: 加密货币ID
            
        Returns:
            解析结果
        """
        try:
            # 下载文件
            file_path = self.download_whitepaper(url, coin_id)
            if not file_path:
                return {"error": "白皮书下载失败"}
            
            # 根据文件类型解析
            if file_path.endswith('.pdf'):
                result = self.parse_pdf(file_path)
            elif file_path.endswith('.html'):
                result = self.parse_html(file_path)
            else:
                return {"error": "不支持的文件格式"}
            
            if "error" in result:
                return result
            
            # 添加元信息
            result["coin_id"] = coin_id
            result["source_url"] = url
            result["file_path"] = file_path
            
            return result
            
        except Exception as e:
            logger.error(f"白皮书解析失败 {url}: {e}")
            return {"error": f"白皮书解析失败: {e}"}


def get_whitepaper_parser() -> WhitepaperParser:
    """获取白皮书解析器实例"""
    return WhitepaperParser()
