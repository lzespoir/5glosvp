import { DownloadOutlined, EyeOutlined, FileOutlined, FileImageOutlined, FileTextOutlined, ExportOutlined } from '@ant-design/icons';
import { Button, Empty, Image } from 'antd';
import { useState } from 'react';

import { resolveApiUrl } from '../../api/client';
import type { ArtifactView } from '../../types/experiment';

export type ArtifactAction = 'view' | 'open' | 'download';

const OPENABLE_EXTENSIONS = ['json', 'yaml', 'yml', 'log', 'txt'];

function extension(name: string): string {
  const idx = name.lastIndexOf('.');
  return idx >= 0 ? name.slice(idx + 1).toLowerCase() : '';
}

/** PNG → 查看；JSON/YAML/log → 打开；其余（NPZ 等二进制）→ 下载，浏览器端不解析 NPZ。 */
export function artifactAction(a: Pick<ArtifactView, 'name' | 'type' | 'media_type'>): ArtifactAction {
  const ext = extension(a.name);
  if (a.media_type.startsWith('image/') || ext === 'png') return 'view';
  if (OPENABLE_EXTENSIONS.includes(ext) || ['json', 'yaml', 'text'].includes(a.type)) return 'open';
  return 'download';
}

function ActionButton({ artifact, onView }: { artifact: ArtifactView; onView: (url: string) => void }) {
  const url = resolveApiUrl(artifact.url);
  const action = artifactAction(artifact);
  switch (action) {
    case 'view':
      return (
        <Button size="small" icon={<EyeOutlined />} onClick={() => onView(url)}>
          查看 View
        </Button>
      );
    case 'open':
      return (
        <Button size="small" icon={<ExportOutlined />} href={url} target="_blank" rel="noopener noreferrer">
          打开 Open
        </Button>
      );
    case 'download':
      return (
        <Button size="small" icon={<DownloadOutlined />} href={url} download={artifact.name}>
          下载 Download
        </Button>
      );
    default: {
      const unreachable: never = action;
      throw new Error(`Unknown artifact action: ${String(unreachable)}`);
    }
  }
}

function artifactIcon(a: ArtifactView) {
  const action = artifactAction(a);
  if (action === 'view') return <FileImageOutlined />;
  if (action === 'open') return <FileTextOutlined />;
  return <FileOutlined />;
}

export function ArtifactsPanel({ artifacts }: { artifacts: ArtifactView[] }) {
  const [previewSrc, setPreviewSrc] = useState<string | null>(null);

  if (artifacts.length === 0) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无产物 / No artifacts" />;
  }

  return (
    <>
      <ul className="artifact-list">
        {artifacts.map((a) => (
          <li key={a.name} className="artifact-list__item">
            <span className="artifact-icon">{artifactIcon(a)}</span>
            <div className="artifact-list__body">
              <code>{a.name}</code>
              <div className="muted artifact-list__desc">{a.description ?? a.media_type}</div>
            </div>
            <ActionButton artifact={a} onView={setPreviewSrc} />
          </li>
        ))}
      </ul>
      {previewSrc && (
        <Image
          className="artifact-preview-hidden"
          src={previewSrc}
          preview={{ open: true, src: previewSrc, onOpenChange: (open) => !open && setPreviewSrc(null) }}
        />
      )}
    </>
  );
}
