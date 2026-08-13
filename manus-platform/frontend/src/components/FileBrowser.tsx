import type { FileEntry } from '../types';

interface FileBrowserProps {
  files: FileEntry[];
}

export function FileBrowser({ files }: FileBrowserProps) {
  // Group by directory
  const grouped = new Map<string, FileEntry[]>();
  for (const file of files) {
    const dir = file.path.includes('/')
      ? file.path.substring(0, file.path.lastIndexOf('/'))
      : '/';
    const existing = grouped.get(dir) ?? [];
    existing.push(file);
    grouped.set(dir, existing);
  }

  return (
    <div className="file-browser-panel">
      <div className="panel-header">
        <h3 className="panel-title-sm">📁 Files</h3>
        <span className="file-count-badge">{files.length}</span>
      </div>

      <div className="file-browser-body">
        {files.length === 0 && (
          <p className="file-browser-empty">No files created yet.</p>
        )}

        {Array.from(grouped.entries()).map(([dir, dirFiles]) => (
          <div key={dir} className="file-group">
            <div className="file-dir-label">{dir}/</div>
            {dirFiles.map((file, i) => {
              const fileName = file.path.includes('/')
                ? file.path.substring(file.path.lastIndexOf('/') + 1)
                : file.path;
              return (
                <div key={i} className="file-entry">
                  <span className="file-icon">
                    {file.action === 'created' ? '✨' : '✏️'}
                  </span>
                  <span className="file-name">{fileName}</span>
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}
