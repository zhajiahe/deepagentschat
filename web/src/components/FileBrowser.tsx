import { ChevronRight, Download, Eye, File, Folder, FolderOpen, Home, RefreshCw, Trash2, Upload, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useToast } from '@/hooks/use-toast';
import request from '@/utils/request';

interface FileInfo {
  filename: string;
  size: number;
  path: string;
  is_dir: boolean;
}

interface FileBrowserProps {
  isOpen: boolean;
  onClose: () => void;
}

export function FileBrowser({ isOpen, onClose }: FileBrowserProps) {
  const [files, setFiles] = useState<FileInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [previewFile, setPreviewFile] = useState<{ name: string; content: string; type: string } | null>(null);
  const [clearDialogOpen, setClearDialogOpen] = useState(false);
  const [currentPath, setCurrentPath] = useState<string>('');
  const { toast } = useToast();

  const loadFiles = async (path: string = '') => {
    try {
      setLoading(true);
      const response = await request.get('/files/list', {
        params: { subdir: path },
      });
      if (response.data.success) {
        setFiles(response.data.data.files);
        setCurrentPath(path);
      }
    } catch (error) {
      console.error('Failed to load files:', error);
      toast({
        title: '加载失败',
        description: '无法加载文件列表',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadFiles(currentPath);
    }
  }, [isOpen]);

  const handleEnterDirectory = (dirPath: string) => {
    loadFiles(dirPath);
  };

  const handleGoUp = () => {
    if (!currentPath) return;
    const parentPath = currentPath.split('/').slice(0, -1).join('/');
    loadFiles(parentPath);
  };

  const handleGoHome = () => {
    loadFiles('');
  };

  const getBreadcrumbs = () => {
    if (!currentPath) return [];
    return currentPath.split('/').filter(Boolean);
  };

  const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      setUploading(true);
      const formData = new FormData();
      formData.append('file', file);

      const response = await request.post('/files/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      if (response.data.success) {
        toast({
          title: '上传成功',
          description: `文件 ${file.name} 已上传`,
        });
        loadFiles(currentPath);
      }
    } catch (error) {
      console.error('Failed to upload file:', error);
      toast({
        title: '上传失败',
        description: '文件上传失败，请重试',
        variant: 'destructive',
      });
    } finally {
      setUploading(false);
      event.target.value = '';
    }
  };

  const getFileType = (filename: string): string => {
    const ext = filename.split('.').pop()?.toLowerCase() || '';
    if (['md', 'markdown'].includes(ext)) return 'markdown';
    if (['json'].includes(ext)) return 'json';
    if (['py', 'js', 'ts', 'tsx', 'jsx', 'java', 'cpp', 'c', 'go', 'rs'].includes(ext)) return 'code';
    if (['csv'].includes(ext)) return 'csv';
    if (['xlsx', 'xls'].includes(ext)) return 'excel';
    if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp'].includes(ext)) return 'image';
    return 'text';
  };

  const handlePreview = async (filePath: string) => {
    try {
      const filename = filePath.split('/').pop() || filePath;
      const fileType = getFileType(filename);

      // Excel 文件不支持预览，提示用户下载
      if (fileType === 'excel') {
        toast({
          title: '不支持预览',
          description: 'Excel 文件不支持在线预览，请下载后查看',
          variant: 'default',
        });
        return;
      }

      // 图片文件使用下载接口获取二进制数据
      if (fileType === 'image') {
        const response = await request.get(`/files/download/${filePath}`, {
          responseType: 'blob',
        });
        const blob = new Blob([response.data]);
        const imageUrl = window.URL.createObjectURL(blob);
        setPreviewFile({ name: filename, content: imageUrl, type: fileType });
        return;
      }

      // 文本文件使用 read 接口
      const response = await request.get(`/files/read/${filePath}`);
      if (response.data.success) {
        const content = response.data.data.content;
        setPreviewFile({ name: filename, content, type: fileType });
      }
    } catch (error) {
      console.error('Failed to preview file:', error);
      toast({
        title: '预览失败',
        description: '文件预览失败，请重试',
        variant: 'destructive',
      });
    }
  };

  const handleDownload = async (filePath: string, filename: string) => {
    try {
      // 使用 download 接口获取二进制文件
      const response = await request.get(`/files/download/${filePath}`, {
        responseType: 'blob',
      });

      // 创建下载链接
      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      toast({
        title: '下载成功',
        description: `文件 ${filename} 已下载`,
      });
    } catch (error) {
      console.error('Failed to download file:', error);
      toast({
        title: '下载失败',
        description: '文件下载失败，请重试',
        variant: 'destructive',
      });
    }
  };

  const handleDelete = async (filePath: string, filename: string, event?: React.MouseEvent) => {
    if (event) event.stopPropagation();

    try {
      const response = await request.delete(`/files/${filePath}`);
      if (response.data.success) {
        toast({
          title: '删除成功',
          description: `${filename} 已删除`,
        });
        loadFiles(currentPath);
      }
    } catch (error) {
      console.error('Failed to delete:', error);
      toast({
        title: '删除失败',
        description: '删除失败，请重试',
        variant: 'destructive',
      });
    }
  };

  const handleClearAll = async () => {
    setClearDialogOpen(false);
    try {
      const response = await request.delete('/files');
      if (response.data.success) {
        toast({
          title: '清空成功',
          description: response.data.data.message,
        });
        loadFiles('');
      }
    } catch (error) {
      console.error('Failed to clear files:', error);
      toast({
        title: '清空失败',
        description: '清空文件失败，请重试',
        variant: 'destructive',
      });
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / k ** i) * 100) / 100 + ' ' + sizes[i];
  };

  if (!isOpen) return null;

  return (
    <div className="fixed right-0 top-0 h-full w-80 bg-background border-l border-border shadow-lg z-50 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border">
        <div className="flex items-center gap-2">
          <FolderOpen className="h-5 w-5" />
          <h2 className="font-semibold">文件浏览器</h2>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* Breadcrumb Navigation */}
      <div className="flex items-center gap-1 p-2 border-b border-border text-sm overflow-x-auto">
        <Button variant="ghost" size="sm" className="h-7 px-2" onClick={handleGoHome} title="根目录">
          <Home className="h-3.5 w-3.5" />
        </Button>
        {getBreadcrumbs().map((part, index) => {
          const path = getBreadcrumbs()
            .slice(0, index + 1)
            .join('/');
          return (
            <div key={path} className="flex items-center gap-1">
              <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
              <Button
                variant="ghost"
                size="sm"
                className="h-7 px-2"
                onClick={() => loadFiles(path)}
                title={part}
              >
                <span className="max-w-[80px] truncate">{part}</span>
              </Button>
            </div>
          );
        })}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 p-4 border-b border-border">
        <label htmlFor="file-upload">
          <Button variant="outline" size="sm" disabled={uploading} asChild>
            <span className="cursor-pointer">
              <Upload className="h-4 w-4 mr-2" />
              上传
            </span>
          </Button>
        </label>
        <input id="file-upload" type="file" className="hidden" onChange={handleUpload} disabled={uploading} />
        <Button variant="outline" size="sm" onClick={() => loadFiles(currentPath)} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          刷新
        </Button>
        <Button variant="outline" size="sm" onClick={() => setClearDialogOpen(true)} disabled={files.length === 0}>
          <Trash2 className="h-4 w-4 mr-2" />
          清空
        </Button>
      </div>

      {/* File List */}
      <ScrollArea className="flex-1 p-4">
        {loading ? (
          <div className="text-center text-muted-foreground py-8">加载中...</div>
        ) : files.length === 0 ? (
          <div className="text-center text-muted-foreground py-8">
            <File className="h-12 w-12 mx-auto mb-2 opacity-50" />
            <p>暂无文件</p>
            <p className="text-sm mt-1">点击上传按钮添加文件</p>
          </div>
        ) : (
          <div className="space-y-2">
            {files.map((file) => (
              <div
                key={file.path}
                className="p-3 rounded-lg border border-border hover:bg-accent transition-colors cursor-pointer"
                onClick={() => {
                  if (file.is_dir) {
                    handleEnterDirectory(file.path);
                  } else {
                    handlePreview(file.path);
                  }
                }}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      {file.is_dir ? (
                        <Folder className="h-4 w-4 flex-shrink-0 text-blue-500" />
                      ) : (
                        <File className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
                      )}
                      <p className="text-sm font-medium truncate" title={file.filename}>
                        {file.filename}
                      </p>
                    </div>
                    {!file.is_dir && <p className="text-xs text-muted-foreground mt-1">{formatFileSize(file.size)}</p>}
                  </div>
                  <div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
                    {!file.is_dir && (
                      <>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          onClick={(e) => {
                            e.stopPropagation();
                            handlePreview(file.path);
                          }}
                          title="预览"
                        >
                          <Eye className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDownload(file.path, file.filename);
                          }}
                          title="下载"
                        >
                          <Download className="h-3.5 w-3.5" />
                        </Button>
                      </>
                    )}
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-destructive hover:text-destructive"
                      onClick={(e) => handleDelete(file.path, file.filename, e)}
                      title="删除"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </ScrollArea>

      {/* Footer */}
      <div className="p-4 border-t border-border text-xs text-muted-foreground text-center">
        共 {files.length} 项
      </div>

      {/* File Preview Dialog */}
      <Dialog
        open={!!previewFile}
        onOpenChange={() => {
          // 如果是图片，释放 blob URL
          if (previewFile?.type === 'image' && previewFile.content.startsWith('blob:')) {
            window.URL.revokeObjectURL(previewFile.content);
          }
          setPreviewFile(null);
        }}
      >
        <DialogContent className="max-w-4xl max-h-[85vh]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <File className="h-5 w-5" />
              {previewFile?.name}
              <span className="text-xs text-muted-foreground ml-2">({previewFile?.type})</span>
            </DialogTitle>
          </DialogHeader>
          <ScrollArea className="h-[70vh] w-full rounded-md border p-4">
            {previewFile?.type === 'image' ? (
              <div className="flex items-center justify-center h-full">
                <img
                  src={previewFile.content}
                  alt={previewFile.name}
                  className="max-w-full max-h-full object-contain"
                  onLoad={() => {
                    // 图片加载完成后释放 blob URL（可选）
                    // window.URL.revokeObjectURL(previewFile.content);
                  }}
                />
              </div>
            ) : previewFile?.type === 'markdown' ? (
              <div
                className="prose prose-sm dark:prose-invert max-w-none"
                dangerouslySetInnerHTML={{
                  __html: previewFile.content
                    .replace(/^### (.*$)/gim, '<h3>$1</h3>')
                    .replace(/^## (.*$)/gim, '<h2>$1</h2>')
                    .replace(/^# (.*$)/gim, '<h1>$1</h1>')
                    .replace(/\*\*(.*)\*\*/gim, '<strong>$1</strong>')
                    .replace(/\*(.*)\*/gim, '<em>$1</em>')
                    .replace(/`([^`]+)`/gim, '<code>$1</code>')
                    .replace(/\n/gim, '<br />'),
                }}
              />
            ) : previewFile?.type === 'json' ? (
              <pre className="text-sm font-mono">{JSON.stringify(JSON.parse(previewFile.content), null, 2)}</pre>
            ) : previewFile?.type === 'csv' ? (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-border">
                  <tbody className="divide-y divide-border">
                    {previewFile.content.split('\n').map((row, i) => (
                      <tr key={i} className={i === 0 ? 'bg-muted font-medium' : ''}>
                        {row.split(',').map((cell, j) => (
                          <td key={j} className="px-3 py-2 text-sm whitespace-nowrap">
                            {cell.trim()}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : previewFile?.type === 'code' ? (
              <pre className="text-sm font-mono bg-muted p-4 rounded-lg overflow-x-auto">
                <code>{previewFile.content}</code>
              </pre>
            ) : (
              <pre className="text-sm whitespace-pre-wrap font-mono">{previewFile?.content}</pre>
            )}
          </ScrollArea>
        </DialogContent>
      </Dialog>

      {/* Clear All Confirmation Dialog */}
      <Dialog open={clearDialogOpen} onOpenChange={setClearDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认清空</DialogTitle>
            <DialogDescription>确定要清空所有文件吗？此操作不可恢复。</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setClearDialogOpen(false)}>
              取消
            </Button>
            <Button variant="destructive" onClick={handleClearAll}>
              确定清空
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
