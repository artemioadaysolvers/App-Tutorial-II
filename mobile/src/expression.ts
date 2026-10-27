import { MAX_VARIABLES_PER_COMPONENT } from './distributions';
export type Expr =
  | { const: number }
  | { var: string }
  | { op: string; args: Expr[] };
export function referencedVariables(n: Expr): Set<string> {
  if ('var' in n) return new Set([n.var]);
  if ('const' in n) return new Set();
  return new Set(n.args.flatMap(a => [...referencedVariables(a)]));
}
const functions = new Set(['abs', 'sqrt', 'log', 'exp', 'sin', 'cos']);
export function parseExpression(source: string, names: string[]): Expr {
  if (!source.trim() || source.length > 500)
    throw Error('Expresión requerida, hasta 500 caracteres.');
  const tokens: string[] = [];
  let rest = source;
  while (rest.length) {
    const m =
      /^\s*(?:(\d+(?:\.\d*)?(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?)|([A-Za-z][A-Za-z0-9_]*)|([()+*/^\-]))/.exec(
        rest,
      );
    if (!m) {
      if (!rest.trim()) break;
      throw Error('Símbolo inválido. Usa punto decimal y * para multiplicar.');
    }
    tokens.push(m[1] || m[2] || m[3]);
    rest = rest.slice(m[0].length);
  }
  let pos = 0,
    nodes = 0;
  function node(v: Expr): Expr {
    if (++nodes > 127) throw Error('Máximo 127 nodos.');
    return v;
  }
  function expression(min = 0, depth = 0): Expr {
    if (depth > 20) throw Error('Expresión demasiado profunda.');
    const t = tokens[pos++];
    let left: Expr;
    if (t === '-')
      left = node({ op: 'neg', args: [expression(30, depth + 1)] });
    else if (t === '+') left = expression(30, depth + 1);
    else if (t === '(') {
      left = expression(0, depth + 1);
      if (tokens[pos++] !== ')') throw Error('Falta cerrar paréntesis.');
    } else if (functions.has(t)) {
      if (tokens[pos++] !== '(')
        throw Error('Las funciones requieren paréntesis.');
      left = node({ op: t, args: [expression(0, depth + 1)] });
      if (tokens[pos++] !== ')') throw Error('Falta cerrar función.');
    } else if (names.includes(t)) left = node({ var: t });
    else if (t && /^(\d|\.)/.test(t)) {
      const n = Number(t);
      if (!Number.isFinite(n) || n > 1e9)
        throw Error('Constante fuera de rango.');
      left = node({ const: n });
    } else throw Error(`Variable o término desconocido: ${t || 'fin'}.`);
    const priorities: Record<string, number> = {
      '+': 10,
      '-': 10,
      '*': 20,
      '/': 20,
      '^': 40,
    };
    const ops: Record<string, string> = {
      '+': 'add',
      '-': 'sub',
      '*': 'mul',
      '/': 'div',
      '^': 'pow',
    };
    while (pos < tokens.length && (priorities[tokens[pos]] ?? -1) >= min) {
      const op = tokens[pos++];
      left = node({
        op: ops[op],
        args: [
          left,
          expression(priorities[op] + (op === '^' ? 0 : 1), depth + 1),
        ],
      });
    }
    return left;
  }
  const ast = expression();
  if (pos !== tokens.length)
    throw Error('Revisa operadores. Ejemplo: 2*X1 + X2.');
  const refs = referencedVariables(ast);
  if (!refs.size) throw Error('Incluye al menos una variable aleatoria.');
  if (refs.size > MAX_VARIABLES_PER_COMPONENT)
    throw Error(
      'Cada componente admite como máximo 5 variables aleatorias distintas.',
    );
  return ast;
}
export function formatExpression(n: Expr): string {
  if ('const' in n) return String(n.const);
  if ('var' in n) return n.var;
  const ops: Record<string, string> = {
    add: '+',
    sub: '-',
    mul: '*',
    div: '/',
    pow: '^',
  };
  if (n.op === 'neg') return `-(${formatExpression(n.args[0])})`;
  if (ops[n.op])
    return `(${formatExpression(n.args[0])} ${ops[n.op]} ${formatExpression(
      n.args[1],
    )})`;
  return `${n.op}(${formatExpression(n.args[0])})`;
}
