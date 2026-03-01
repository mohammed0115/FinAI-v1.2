import type { ReactNode } from "react";

type PageHeaderProps = {
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
};

export default function PageHeader({ title, description, action }: PageHeaderProps) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold text-app-text">{title}</h1>
        {description ? <p className="text-sm text-app-textSecondary">{description}</p> : null}
      </div>
      {action ? <div>{action}</div> : null}
    </div>
  );
}
