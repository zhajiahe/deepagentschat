import { useState, useEffect } from 'react';
import { X, Upload, Download, Trash2, RefreshCw, File, FolderOpen, Eye } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { useToast } from '@/hooks/use-toast';
import request from '@/utils/request';

interface FileInfo {
  filename: string;
  size: number;
  path: string;
}

interface FileBrowserProps {
  isOpen: boolean;
  onClose: () => void;
}

export function FileBrowser({ isOpen, onClose }: FileBrowserProps) {
  const [files, setFiles] = useState<FileInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [previewFile, setPreviewFile] = useState<{ name: string; content: string } | null>(null);
  const { toast } = useToast();

  const loadFiles = async () => {
    try {
      setLoading(true);
      const response = await request.get('/files/list');
      if (response.data.success) {
        setFiles(response.data.data.files);
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
      loadFiles();
    }
  }, [isOpen]);

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
        loadFiles();
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
      // Reset input
      event.target.value = '';
    }
  };

  const handlePreview = async (filename: string) => {
    try {
      const response = await request.get(`/files/read/${filename}`);
      if (response.data.success) {
        const content = response.data.data.content;
        setPreviewFile({ name: filename, content });
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

  const handleDownload = async (filename: string) => {
    try {
      const response = await request.get(`/files/read/${filename}`);
      if (response.data.success) {
        const content = response.data.data.content;
        // 创建 Blob 并下载
        const blob = new Blob([content], { type: 'text/plain' });
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
      }
    } catch (error) {
      console.error('Failed to download file:', error);
      toast({
        title: '下载失败',
        description: '文件下载失败，请重试',
        variant: 'destructive',
      });
    }
  };

  const handleDelete = async (filename: string, event?: React.MouseEvent) => {
    if (event) event.stopPropagation();

    try {
      const response = await request.delete(`/files/${filename}`);
      if (response.data.success) {
        toast({
          title: '删除成功',
          description: `文件 ${filename} 已删除`,
        });
        loadFiles();
      }
    } catch (error) {
      console.error('Failed to delete file:', error);
      toast({
        title: '删除失败',
        description: '文件删除失败，请重试',
        variant: 'destructive',
      });
    }
  };

  const handleClearAll = async () => {

    try {
      const response = await request.delete('/files');
      if (response.data.success) {
        toast({
          title: '清空成功',
          description: response.data.data.message,
        });
        loadFiles();
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
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
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
        <input
          id="file-upload"
          type="file"
          className="hidden"
          onChange={handleUpload}
          disabled={uploading}
        />
        <Button variant="outline" size="sm" onClick={loadFiles} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          刷新
        </Button>
        <Button variant="outline" size="sm" onClick={handleClearAll} disabled={files.length === 0}>
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
                onClick={() => handlePreview(file.filename)}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <File className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
                      <p className="text-sm font-medium truncate" title={file.filename}>
                        {file.filename}
                      </p>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {formatFileSize(file.size)}
                    </p>
                  </div>
                  <div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={(e) => {
                        e.stopPropagation();
                        handlePreview(file.filename);
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
                        handleDownload(file.filename);
                      }}
                      title="下载"
                    >
                      <Download className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-destructive hover:text-destructive"
                      onClick={(e) => handleDelete(file.filename, e)}
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
        共 {files.length} 个文件
      </div>

      {/* File Preview Dialog */}
      <Dialog open={!!previewFile} onOpenChange={() => setPreviewFile(null)}>
        <DialogContent className="max-w-3xl max-h-[80vh]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <File className="h-5 w-5" />
              {previewFile?.name}
            </DialogTitle>
          </DialogHeader>
          <ScrollArea className="h-[60vh] w-full rounded-md border p-4">
            <pre className="text-sm whitespace-pre-wrap font-mono">
              {previewFile?.content}
            </pre>
          </ScrollArea>
        </DialogContent>
      </Dialog>
    </div>
  );
}
