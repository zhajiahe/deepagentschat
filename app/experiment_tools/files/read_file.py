"""
文件读取工具
用法: python read_file.py <filename>
"""

import sys
from pathlib import Path

MAX_CHARS = 2000


def main():
    if len(sys.argv) < 2:
        print("用法: python read_file.py <filename>")
        sys.exit(1)

    filename = sys.argv[1]
    filepath = Path(filename)

    # 检查文件是否存在
    if not filepath.exists():
        print(f"❌ 文件不存在: {filename}", file=sys.stderr)
        sys.exit(1)

    # 检查是否是文件（而非目录）
    if not filepath.is_file():
        print(f"❌ 不是文件: {filename}", file=sys.stderr)
        sys.exit(1)

    # 检查文件大小
    file_size = filepath.stat().st_size
    if file_size == 0:
        print("⚠️  文件为空")
        return

    # 大文件警告（超过 10MB）
    if file_size > 10 * 1024 * 1024:
        print(f"⚠️  文件较大 ({file_size / 1024 / 1024:.1f} MB)，建议使用:")
        print(f"   head -n 100 {filename}")
        print(f"   tail -n 100 {filename}")
        print(f"   grep 'keyword' {filename}")
        sys.exit(1)

    # 尝试读取文件
    try:
        content = read_file_with_fallback(filepath)

        if len(content) > MAX_CHARS:
            print(content[:MAX_CHARS])
            print(f"\n... [已截断. 总长度: {len(content):,} 字符 / {file_size:,} 字节]")
            print(f"💡 查看完整内容: cat {filename}")
        else:
            print(content)

    except PermissionError:
        print(f"❌ 权限不足: {filename}", file=sys.stderr)
        sys.exit(1)

    except IsADirectoryError:
        print(f"❌ 这是一个目录: {filename}", file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        print(f"❌ 读取失败: {e}", file=sys.stderr)
        sys.exit(1)


def read_file_with_fallback(filepath: Path) -> str:
    """
    尝试多种编码读取文件
    优先级: utf-8 > gbk > latin-1
    """
    encodings = ["utf-8", "gbk", "gb2312", "latin-1"]

    for encoding in encodings:
        try:
            with open(filepath, encoding=encoding) as f:
                content = f.read()

            # 成功读取，显示编码信息（如果不是 utf-8）
            if encoding != "utf-8":
                print(f"ℹ️  检测到编码: {encoding}\n", file=sys.stderr)

            return content

        except UnicodeDecodeError:
            continue
        except Exception as e:
            raise e

    # 所有编码都失败，尝试二进制模式
    raise UnicodeDecodeError("unknown", b"", 0, 1, "无法识别文件编码，可能是二进制文件")


if __name__ == "__main__":
    main()
