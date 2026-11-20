import express from 'express';
import fs from 'fs';
import path from 'path';
import { spawn } from 'child_process';
import { createServer as createViteServer } from 'vite';
import { describePluginFileRole } from './src/lib/aetherloomLogic.ts';
import type { PluginFileEntry } from './src/types.ts';

const ROOT_DIR = process.cwd();
const PLUGIN_DIR = path.join(ROOT_DIR, 'aetherloom');
const CLI_BRIDGE = path.join(PLUGIN_DIR, 'cli_bridge.py');

const IGNORED_DIRS = new Set(['__pycache__', 'data', 'runs', 'dream_diffs', '.pytest_cache']);

function walkPluginTree(dir: string, base: string = dir): PluginFileEntry[] {
  if (!fs.existsSync(dir)) return [];
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  const results: PluginFileEntry[] = [];

  for (const entry of entries) {
    if (IGNORED_DIRS.has(entry.name)) continue;
    const absPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...walkPluginTree(absPath, base));
    } else if (entry.isFile()) {
      const relPath = path.relative(base, absPath).split(path.sep).join('/');
      const content = fs.readFileSync(absPath, 'utf-8');
      const meta = describePluginFileRole(relPath);
      results.push({
        path: relPath,
        category: meta.category,
        role: meta.role,
        sizeBytes: Buffer.byteLength(content, 'utf-8'),
        lines: content.split('\n').length,
        content,
      });
    }
  }

  return results.sort((a, b) => a.path.localeCompare(b.path));
}

function runPythonBridge(action: string, payload: Record<string, unknown> = {}): Promise<unknown> {
  return new Promise((resolve, reject) => {
    const child = spawn('python3', [CLI_BRIDGE, action], {
      cwd: PLUGIN_DIR,
      stdio: ['pipe', 'pipe', 'pipe'],
    });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (chunk) => {
      stdout += chunk.toString('utf-8');
    });
    child.stderr.on('data', (chunk) => {
      stderr += chunk.toString('utf-8');
    });
    child.on('error', (err) => reject(err));
    child.on('close', (code) => {
      try {
        const parsed = stdout.trim() ? JSON.parse(stdout) : {};
        if (code !== 0) {
          reject(new Error(parsed.error || stderr || `Bridge exited with status ${code}`));
          return;
        }
        resolve(parsed);
      } catch (err) {
        reject(new Error(`Failed to parse bridge output: ${stderr || stdout || String(err)}`));
      }
    });
    child.stdin.write(JSON.stringify(payload));
    child.stdin.end();
  });
}

async function startServer() {
  const app = express();
  const PORT = 3000;

  app.use(express.json({ limit: '1mb' }));

  app.get('/api/tree', (_req, res) => {
    try {
      const files = walkPluginTree(PLUGIN_DIR);
      res.json({ root: 'aetherloom', count: files.length, files });
    } catch (err) {
      res.status(500).json({ error: String(err) });
    }
  });

  app.get('/api/download-zip', (_req, res) => {
    const pyScript = `
import io, pathlib, sys, zipfile
root = pathlib.Path(sys.argv[1])
ignored = {'__pycache__', 'data', 'runs', 'dream_diffs', '.pytest_cache'}
buf = io.BytesIO()
with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
    for p in sorted(root.rglob('*')):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if any(part in ignored for part in rel.parts):
            continue
        zf.write(p, arcname=str(pathlib.Path('aetherloom') / rel))
sys.stdout.buffer.write(buf.getvalue())
`;
    const child = spawn('python3', ['-c', pyScript, PLUGIN_DIR], {
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    const chunks: Buffer[] = [];
    let stderr = '';
    child.stdout.on('data', (chunk: Buffer) => chunks.push(chunk));
    child.stderr.on('data', (chunk: Buffer) => {
      stderr += chunk.toString('utf-8');
    });
    child.on('error', (err) => res.status(500).json({ error: String(err) }));
    child.on('close', (code) => {
      if (code !== 0) {
        res.status(500).json({ error: stderr || 'Failed to package plugin zip.' });
        return;
      }
      const zipBuffer = Buffer.concat(chunks);
      res.setHeader('Content-Type', 'application/zip');
      res.setHeader('Content-Disposition', 'attachment; filename="aetherloom-supergravity-plugin.zip"');
      res.setHeader('Content-Length', String(zipBuffer.length));
      res.send(zipBuffer);
    });
  });

  app.get('/api/bundle', (_req, res) => {
    try {
      const files = walkPluginTree(PLUGIN_DIR);
      res.setHeader('Content-Type', 'application/json');
      res.setHeader('Content-Disposition', 'attachment; filename="aetherloom-supergravity-plugin.json"');
      res.send(
        JSON.stringify(
          {
            plugin: 'aetherloom',
            command: '/supergravity',
            generatedAt: new Date().toISOString(),
            fileCount: files.length,
            files: files.map((f) => ({
              path: `aetherloom/${f.path}`,
              role: f.role,
              content: f.content,
            })),
          },
          null,
          2,
        ),
      );
    } catch (err) {
      res.status(500).json({ error: String(err) });
    }
  });

  app.get('/api/state', async (req, res) => {
    try {
      const deposited = Number(req.query.billing_deposited_usd ?? 0);
      const tierKey = req.query.tier === 'paid' ? 'AIzaPaid_key' : 'AIzaFree_default';
      const data = await runPythonBridge('state', {
        api_key: tierKey,
        billing_deposited_usd: Number.isFinite(deposited) ? deposited : 0,
      });
      res.json(data);
    } catch (err) {
      res.status(500).json({ error: String(err) });
    }
  });

  app.post('/api/orchestrate', async (req, res) => {
    try {
      const data = await runPythonBridge('orchestrate', req.body ?? {});
      res.json(data);
    } catch (err) {
      res.status(400).json({ error: String(err) });
    }
  });

  app.post('/api/warden/check', async (req, res) => {
    try {
      const data = await runPythonBridge('warden_check', req.body ?? {});
      res.json(data);
    } catch (err) {
      res.status(400).json({ error: String(err) });
    }
  });

  app.post('/api/natalie/decide', async (req, res) => {
    try {
      const data = await runPythonBridge('natalie_decide', req.body ?? {});
      res.json(data);
    } catch (err) {
      res.status(400).json({ error: String(err) });
    }
  });

  app.post('/api/natalie/cap', async (req, res) => {
    try {
      const data = await runPythonBridge('natalie_set_cap', req.body ?? {});
      res.json(data);
    } catch (err) {
      res.status(400).json({ error: String(err) });
    }
  });

  app.post('/api/memory/search', async (req, res) => {
    try {
      const data = await runPythonBridge('memory_search', req.body ?? {});
      res.json(data);
    } catch (err) {
      res.status(400).json({ error: String(err) });
    }
  });

  app.post('/api/memory/note', async (req, res) => {
    try {
      const data = await runPythonBridge('memory_add_note', req.body ?? {});
      res.json(data);
    } catch (err) {
      res.status(400).json({ error: String(err) });
    }
  });

  app.post('/api/dream/preview', async (req, res) => {
    try {
      const data = await runPythonBridge('dream_preview', req.body ?? {});
      res.json(data);
    } catch (err) {
      res.status(400).json({ error: String(err) });
    }
  });

  app.post('/api/dream/approve', async (req, res) => {
    try {
      const data = await runPythonBridge('dream_approve', req.body ?? {});
      res.json(data);
    } catch (err) {
      res.status(400).json({ error: String(err) });
    }
  });

  app.post('/api/skills/evaluate', async (req, res) => {
    try {
      const data = await runPythonBridge('skill_evaluate', req.body ?? {});
      res.json(data);
    } catch (err) {
      res.status(400).json({ error: String(err) });
    }
  });

  app.post('/api/adapters/rebuild', async (_req, res) => {
    try {
      const data = await runPythonBridge('build_adapters', {});
      res.json(data);
    } catch (err) {
      res.status(500).json({ error: String(err) });
    }
  });

  app.post('/api/acceptance/run', async (_req, res) => {
    try {
      const data = await runPythonBridge('run_acceptance', {});
      res.json(data);
    } catch (err) {
      res.status(500).json({ error: String(err) });
    }
  });

  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(ROOT_DIR, 'dist');
    app.use(express.static(distPath));
    app.get('*', (_req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`AetherLoom Workbench running on http://localhost:${PORT}`);
  });
}

startServer();
