import { BotIcon } from 'lucide-react';

interface EmptyStateProps {
  onNewChat?: () => void;
}

export const EmptyState = ({ onNewChat }: EmptyStateProps) => {
  return (
    <div className="flex-1 flex flex-col items-center justify-center bg-background dark:bg-grokbg p-4">
      <div className="w-32 h-32 mb-12 opacity-90 flex items-center justify-center">
        <div className="w-24 h-24 bg-gradient-to-br from-primary to-primary/60 rounded-full flex items-center justify-center shadow-lg">
          <BotIcon className="w-12 h-12 text-white" />
        </div>
      </div>
      <h1 className="text-4xl font-bold mb-4 text-foreground dark:text-groktext">How can I help you today?</h1>
      <p className="text-lg text-muted-foreground dark:text-groksub">开始新的对话，探索 AI 的无限可能</p>
    </div>
  );
};
