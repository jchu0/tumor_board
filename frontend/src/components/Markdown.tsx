/**
 * Minimal Markdown renderer for the authored clinical documents.
 *
 * Deliberately not a dependency: the corpus in data/cases/ uses headings, GFM
 * tables (every lab report is one), bold, bullets and paragraphs — and nothing
 * else. A ~90-line renderer covers it and keeps `npm install` to react alone.
 *
 * Unsupported syntax degrades to plain text rather than throwing, so an
 * unexpected construct in a document can never blank the panel.
 */

function inline(text: string): (string | JSX.Element)[] {
  // **bold** and `code`, applied in one pass so they can't nest incorrectly.
  const parts: (string | JSX.Element)[] = [];
  const re = /(\*\*([^*]+)\*\*|`([^`]+)`)/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let key = 0;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) parts.push(text.slice(last, m.index));
    if (m[2] !== undefined) parts.push(<strong key={key++}>{m[2]}</strong>);
    else parts.push(<code key={key++}>{m[3]}</code>);
    last = m.index + m[0].length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts.length ? parts : [text];
}

function splitRow(line: string): string[] {
  return line.replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
}

const isDivider = (line: string) => /^\|?[\s:-]*-[\s:|-]*\|?$/.test(line) && line.includes("-");

export function Markdown({ source }: { source: string }) {
  const lines = source.replace(/\r\n/g, "\n").split("\n");
  const out: JSX.Element[] = [];
  let para: string[] = [];
  let list: string[] = [];
  let key = 0;

  const flushPara = () => {
    if (para.length) {
      out.push(<p key={key++}>{inline(para.join(" "))}</p>);
      para = [];
    }
  };
  const flushList = () => {
    if (list.length) {
      out.push(
        <ul key={key++}>
          {list.map((li, i) => (
            <li key={i}>{inline(li)}</li>
          ))}
        </ul>
      );
      list = [];
    }
  };
  const flush = () => {
    flushPara();
    flushList();
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    if (!trimmed) {
      flush();
      continue;
    }

    const heading = /^(#{1,4})\s+(.*)$/.exec(trimmed);
    if (heading) {
      flush();
      const level = heading[1].length;
      const text = inline(heading[2].replace(/--/g, "—"));
      out.push(
        level === 1 ? <h3 key={key++}>{text}</h3>
        : level === 2 ? <h4 key={key++}>{text}</h4>
        : <h5 key={key++}>{text}</h5>
      );
      continue;
    }

    // GFM table: a header row followed by a divider row.
    if (trimmed.startsWith("|") && i + 1 < lines.length && isDivider(lines[i + 1].trim())) {
      flush();
      const head = splitRow(trimmed);
      const rows: string[][] = [];
      i += 2;
      while (i < lines.length && lines[i].trim().startsWith("|")) {
        rows.push(splitRow(lines[i].trim()));
        i++;
      }
      i--;
      out.push(
        <div className="md-table-wrap" key={key++}>
          <table className="md-table">
            <thead>
              <tr>{head.map((h, j) => <th key={j}>{inline(h)}</th>)}</tr>
            </thead>
            <tbody>
              {rows.map((r, ri) => (
                <tr key={ri}>{r.map((c, ci) => <td key={ci}>{inline(c)}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      continue;
    }

    const bullet = /^[-*]\s+(.*)$/.exec(trimmed);
    if (bullet) {
      flushPara();
      list.push(bullet[1]);
      continue;
    }

    if (/^(-{3,}|_{3,})$/.test(trimmed)) {
      flush();
      out.push(<hr key={key++} />);
      continue;
    }

    flushList();
    para.push(trimmed);
  }
  flush();

  return <div className="md">{out}</div>;
}
