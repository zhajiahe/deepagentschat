"""
URL 内容读取工具
用法: python read_url.py <url> [options]
"""

import argparse
import socket
import ssl
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

# 常量配置
MAX_CONTENT_SIZE = 10 * 1024 * 1024  # 10MB
MAX_DISPLAY_CHARS = 5000
DEFAULT_TIMEOUT = 30
USER_AGENT = "Mozilla/5.0 (compatible; AI-DB-Tools/1.0)"


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="读取并显示 URL 内容",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python read_url.py https://example.com
  python read_url.py https://api.github.com/repos/python/cpython --timeout 60
  python read_url.py https://example.com --max-size 5000000
  python read_url.py https://example.com --save output.html
  python read_url.py https://example.com --headers "Authorization: Bearer token"
        """,
    )

    parser.add_argument("url", help="要读取的 URL")
    parser.add_argument(
        "--timeout", type=int, default=DEFAULT_TIMEOUT, help=f"请求超时时间（秒），默认 {DEFAULT_TIMEOUT}"
    )
    parser.add_argument(
        "--max-size", type=int, default=MAX_CONTENT_SIZE, help=f"最大内容大小（字节），默认 {MAX_CONTENT_SIZE}"
    )
    parser.add_argument(
        "--max-display", type=int, default=MAX_DISPLAY_CHARS, help=f"最大显示字符数，默认 {MAX_DISPLAY_CHARS}"
    )
    parser.add_argument("--save", type=str, help="保存内容到文件")
    parser.add_argument("--headers", action="append", help='添加 HTTP 请求头（格式: "Key: Value"）')
    parser.add_argument("--no-verify-ssl", action="store_true", help="跳过 SSL 证书验证（不推荐）")
    parser.add_argument("--follow-redirects", action="store_true", default=True, help="跟随重定向（默认启用）")
    parser.add_argument("--show-headers", action="store_true", help="显示响应头信息")

    return parser.parse_args()


def validate_url(url: str) -> bool:
    """验证 URL 格式"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc]) and result.scheme in ["http", "https"]
    except Exception:
        return False


def get_content_type(headers) -> str:  # type: ignore[no-untyped-def]
    """获取内容类型"""
    content_type = str(headers.get("Content-Type", ""))
    if ";" in content_type:
        content_type = content_type.split(";")[0].strip()
    return content_type


def is_text_content(content_type: str) -> bool:
    """判断是否为文本内容"""
    text_types = ["text/", "application/json", "application/xml", "application/javascript", "application/x-yaml"]
    return any(content_type.startswith(t) for t in text_types)


def detect_encoding(headers, content: bytes) -> str:  # type: ignore[no-untyped-def]
    """检测内容编码"""
    # 1. 从 Content-Type header 获取
    content_type = str(headers.get("Content-Type", ""))
    if "charset=" in content_type:
        charset = content_type.split("charset=")[-1].split(";")[0].strip()
        return charset

    # 2. 从 HTML meta 标签检测
    try:
        content_str = content[:1024].decode("utf-8", errors="ignore")
        if "charset=" in content_str.lower():
            import re

            match = re.search(r'charset=["\']?([^"\'>\s]+)', content_str, re.IGNORECASE)
            if match:
                return match.group(1)
    except Exception:
        pass

    # 3. 默认使用 utf-8
    return "utf-8"


def format_size(size_bytes: int) -> str:
    """格式化文件大小"""
    size_float = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if size_float < 1024.0:
            return f"{size_float:.1f} {unit}"
        size_float /= 1024.0
    return f"{size_float:.1f} TB"


def read_url(url: str, args) -> tuple:
    """
    读取 URL 内容
    返回: (content, headers, status_code)
    """
    # 创建请求
    request = Request(url)
    request.add_header("User-Agent", USER_AGENT)

    # 添加自定义请求头
    if args.headers:
        for header in args.headers:
            if ":" in header:
                key, value = header.split(":", 1)
                request.add_header(key.strip(), value.strip())

    # SSL 上下文
    context = None
    if args.no_verify_ssl:
        context = ssl._create_unverified_context()
        print("⚠️  警告: SSL 证书验证已禁用", file=sys.stderr)

    # 发送请求
    try:
        response = urlopen(request, timeout=args.timeout, context=context)
    except HTTPError as e:
        raise Exception(f"HTTP 错误 {e.code}: {e.reason}") from e
    except URLError as e:
        if isinstance(e.reason, socket.timeout):
            raise Exception(f"请求超时（{args.timeout}秒）") from e
        raise Exception(f"URL 错误: {e.reason}") from e
    except TimeoutError as e:
        raise Exception(f"连接超时（{args.timeout}秒）") from e

    # 检查内容大小
    content_length = response.headers.get("Content-Length")
    if content_length:
        size = int(content_length)
        if size > args.max_size:
            raise Exception(f"内容过大 ({format_size(size)})，超过限制 ({format_size(args.max_size)})")

    # 读取内容
    content = b""
    chunk_size = 8192
    total_read = 0

    while True:
        chunk = response.read(chunk_size)
        if not chunk:
            break

        content += chunk
        total_read += len(chunk)

        if total_read > args.max_size:
            raise Exception(f"内容超过大小限制 ({format_size(args.max_size)})")

    return content, response.headers, response.getcode()


def display_content(content: bytes, headers, args):
    """显示内容"""
    content_type = get_content_type(headers)

    # 显示响应头
    if args.show_headers:
        print("=" * 60)
        print("响应头:")
        print("=" * 60)
        for key, value in headers.items():
            print(f"{key}: {value}")
        print("=" * 60)
        print()

    # 检查是否为文本内容
    if not is_text_content(content_type):
        print(f"⚠️  非文本内容类型: {content_type}")
        print(f"📦 内容大小: {format_size(len(content))}")

        if args.save:
            print("💡 使用 --save 选项保存到文件")
        else:
            print("💡 建议使用 --save 选项保存二进制内容")
        return

    # 解码文本内容
    encoding = detect_encoding(headers, content)

    try:
        text = content.decode(encoding)
    except UnicodeDecodeError:
        # 尝试其他编码
        for fallback_encoding in ["utf-8", "gbk", "gb2312", "latin-1"]:
            try:
                text = content.decode(fallback_encoding)
                encoding = fallback_encoding
                print(f"ℹ️  使用编码: {encoding}", file=sys.stderr)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise Exception("无法解码内容，尝试了多种编码")

    # 显示内容
    if len(text) > args.max_display:
        print(text[: args.max_display])
        print(f"\n... [已截断. 总长度: {len(text):,} 字符 / {format_size(len(content))}]")
        print(f"💡 使用 --max-display {len(text)} 查看完整内容")
        print("💡 或使用 --save 保存到文件")
    else:
        print(text)

        if len(text) > 1000:
            print(f"\n📊 {len(text):,} 字符 / {format_size(len(content))}")


def save_content(content: bytes, filepath: str):
    """保存内容到文件"""
    try:
        output_path = Path(filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "wb") as f:
            f.write(content)

        print(f"✅ 已保存到: {output_path.absolute()}")
        print(f"📦 文件大小: {format_size(len(content))}")
    except Exception as e:
        raise Exception(f"保存文件失败: {e}") from e


def main():
    """主函数"""
    args = parse_args()

    # 验证 URL
    if not validate_url(args.url):
        print("❌ 无效的 URL 格式", file=sys.stderr)
        print("💡 URL 必须以 http:// 或 https:// 开头", file=sys.stderr)
        sys.exit(1)

    # 显示请求信息
    print(f"🌐 正在请求: {args.url}", file=sys.stderr)

    try:
        # 读取 URL
        content, headers, status_code = read_url(args.url, args)

        print(f"✅ HTTP {status_code}", file=sys.stderr)
        print(f"📦 大小: {format_size(len(content))}", file=sys.stderr)
        print(f"📄 类型: {get_content_type(headers)}", file=sys.stderr)
        print(file=sys.stderr)

        # 保存或显示
        if args.save:
            save_content(content, args.save)
        else:
            display_content(content, headers, args)

    except KeyboardInterrupt:
        print("\n❌ 用户中断", file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        print(f"❌ 错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
