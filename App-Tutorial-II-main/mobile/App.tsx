import React, { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Modal,
  Pressable,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import {
  getAuth,
  GoogleAuthProvider,
  onAuthStateChanged,
  signInWithCredential,
  signOut,
  User,
} from '@react-native-firebase/auth';
import {
  GoogleSignin,
  isSuccessResponse,
} from '@react-native-google-signin/google-signin';
import { config } from './src/config';
import { api, Experiment, Spec, Summary, Usage, components } from './src/api';
import JointHistogram from './src/JointHistogramChart';
import {
  distributions,
  makeVariable,
  Variable,
  MAX_VARIABLES_PER_COMPONENT,
} from './src/distributions';
import {
  formatExpression,
  parseExpression,
  referencedVariables,
} from './src/expression';
import { histogram } from './src/histogram';

const message = (e: unknown) =>
  e instanceof Error ? e.message : 'No se pudo completar la operación.';
function Button({
  label,
  onPress,
  disabled = false,
  secondary = false,
}: {
  label: string;
  onPress: () => void;
  disabled?: boolean;
  secondary?: boolean;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled }}
      disabled={disabled}
      onPress={onPress}
      style={[s.button, secondary && s.secondary, disabled && s.disabled]}
    >
      <Text style={[s.buttonText, secondary && s.ink]}>{label}</Text>
    </Pressable>
  );
}
function Field({
  label,
  value,
  onChange,
  multiline = false,
}: {
  label: string;
  value: string;
  onChange: (t: string) => void;
  multiline?: boolean;
}) {
  return (
    <View style={s.field}>
      <Text style={s.label}>{label}</Text>
      <TextInput
        accessibilityLabel={label}
        autoCapitalize="none"
        autoCorrect={false}
        value={value}
        onChangeText={onChange}
        multiline={multiline}
        style={[s.input, multiline && { minHeight: 75 }]}
      />
    </View>
  );
}
function describeVariable(v: Variable): string {
  return distributions
    .find(d => d.id === v.distribution)!
    .fields.map(([key, label]) => {
      const value =
        v.params[key] ??
        (v.distribution === 'lognormal' && key === 'mu'
          ? v.params.mean
          : undefined);
      return `${label}: ${Array.isArray(value) ? value.join(', ') : value}`;
    })
    .join('\n');
}
function AppContent() {
  const [user, setUser] = useState<User | null>(null),
    [initial, setInitial] = useState(config.configured);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(''),
    [items, setItems] = useState<Summary[]>([]),
    [loaded, setLoaded] = useState(false);
  const [page, setPage] = useState<'list' | 'new' | 'detail'>('list'),
    [title, setTitle] = useState('Mi experimento');
  const [vars, setVars] = useState<Variable[]>([]),
    [expressions, setExpressions] = useState(['X1 + X2']);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [picker, setPicker] = useState(false),
    [dist, setDist] = useState(distributions[0]);
  const [fields, setFields] = useState<Record<string, string>>(
    Object.fromEntries(distributions[0].fields.map(([k, , v]) => [k, v])),
  );
  const [min, setMin] = useState(''),
    [max, setMax] = useState(''),
    [detail, setDetail] = useState<Experiment | null>(null),
    [binText, setBinText] = useState('10');
  const pending = useRef<{ spec: Spec; key: string } | null>(null),
    session = useRef(0);
  useEffect(() => {
    if (!config.configured) return;
    GoogleSignin.configure({ webClientId: config.webClientId });
    return onAuthStateChanged(getAuth(), value => {
      session.current++;
      setUser(value);
      setInitial(false);
      setItems([]);
      setUsage(null);
      setLoaded(false);
      setDetail(null);
      setPage('list');
      pending.current = null;
    });
  }, []);
  async function refresh() {
    const generation = session.current,
      [records, quota] = await Promise.all([
        api<Summary[]>(''),
        api<Usage>('', 'GET', undefined, undefined, '/v1/usage'),
      ]);
    if (generation === session.current) {
      setItems(records);
      setUsage(quota);
      setLoaded(true);
    }
  }
  useEffect(() => {
    if (user) {
      setBusy(true);
      refresh()
        .catch(e => setError(message(e)))
        .finally(() => setBusy(false));
    }
  }, [user]); // eslint-disable-line react-hooks/exhaustive-deps
  async function action(fn: () => Promise<void>) {
    setBusy(true);
    setError('');
    try {
      await fn();
    } catch (e) {
      setError(message(e));
    } finally {
      setBusy(false);
    }
  }
  async function login() {
    await GoogleSignin.hasPlayServices({ showPlayServicesUpdateDialog: true });
    const result = await GoogleSignin.signIn();
    if (isSuccessResponse(result) && result.data.idToken)
      await signInWithCredential(
        getAuth(),
        GoogleAuthProvider.credential(result.data.idToken),
      );
  }
  function addVariable() {
    try {
      if (vars.length >= MAX_VARIABLES_PER_COMPONENT * expressions.length)
        throw Error(
          `Máximo ${
            MAX_VARIABLES_PER_COMPONENT * expressions.length
          } variables para ${
            expressions.length
          } componente(s); 5 distintas por componente.`,
        );
      const name = Array.from({ length: 15 }, (_, i) => `X${i + 1}`).find(
        n => !vars.some(v => v.name === n),
      )!;
      setVars([...vars, makeVariable(name, dist, fields, min, max)]);
      setMin('');
      setMax('');
      setError('');
    } catch (e) {
      setError(message(e));
    }
  }
  async function simulate() {
    if (!title.trim() || title.trim().length > 80)
      throw Error('Título obligatorio, hasta 80 caracteres.');
    if (!vars.length) throw Error('Agrega al menos una variable.');
    const spec: Spec = {
      version: 2,
      title: title.trim(),
      variables: vars,
      expressions: expressions.map(expression =>
        parseExpression(
          expression,
          vars.map(v => v.name),
        ),
      ),
      samples: 100,
    };
    if (vars.length > MAX_VARIABLES_PER_COMPONENT * expressions.length)
      throw Error(
        'Demasiadas variables para el número de componentes: máximo 5 por componente.',
      );
    const used = new Set(
      spec.expressions.flatMap(e => [...referencedVariables(e)]),
    );
    if (vars.some(v => !used.has(v.name)))
      throw Error(
        'Usa todas las variables definidas o quita las que no se utilizan.',
      );
    if (
      !pending.current ||
      JSON.stringify(pending.current.spec) !== JSON.stringify(spec)
    ) {
      const key = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
        const r = Math.floor(Math.random() * 16);
        return (c === 'x' ? r : (r & 3) | 8).toString(16);
      });
      pending.current = { spec, key };
    }
    let saved: Experiment;
    try {
      saved = await api<Experiment>('', 'POST', spec, pending.current.key);
    } catch (e) {
      await refresh().catch(() => {});
      throw e;
    }
    pending.current = null;
    setDetail(saved);
    setBinText('10');
    setPage('detail');
    await refresh();
  }
  function remove(eid: string) {
    Alert.alert(
      'Eliminar experimento',
      'Se eliminará también de la base de datos. Esta acción no se puede deshacer.',
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Eliminar',
          style: 'destructive',
          onPress: () =>
            action(async () => {
              await api('/' + eid, 'DELETE');
              setDetail(null);
              setPage('list');
              await refresh();
            }),
        },
      ],
    );
  }
  const header = (
    <View style={s.header}>
      <Text style={s.eyebrow}>LABORATORIO / MONTE CARLO</Text>
      <Text style={s.brand}>
        azar<Text style={s.accent}>.</Text>
      </Text>
      <Text style={s.subtitle}>Ideas simbólicas. Cien resultados.</Text>
    </View>
  );
  if (!config.configured)
    return (
      <SafeAreaView style={s.root}>
        <ScrollView contentContainerStyle={s.container}>
          {header}
          <Text style={s.h1}>Conecta tu laboratorio</Text>
          <Text style={s.body}>
            Agrega tu google-services.json, ejecuta el paso de configuración del
            manual y vuelve a compilar.
          </Text>
          <Text style={s.note}>
            React Native nativo · TypeScript · Python + NumPy
          </Text>
        </ScrollView>
      </SafeAreaView>
    );
  if (initial)
    return (
      <SafeAreaView style={s.root}>
        <ActivityIndicator accessibilityLabel="Cargando sesión" />
      </SafeAreaView>
    );
  if (!user)
    return (
      <SafeAreaView style={s.root}>
        <StatusBar barStyle="dark-content" />
        <ScrollView contentContainerStyle={s.container}>
          {header}
          <Text style={s.h1}>Explora lo{'\n'}impredecible.</Text>
          <Text style={s.body}>
            Define variables aleatorias, escribe una expresión y observa cómo se
            distribuyen sus resultados.
          </Text>
          <View style={s.card}>
            <Text style={s.cardTitle}>Tu pequeño laboratorio</Text>
            <Text style={s.body}>
              12 distribuciones{'\n'}5 variables por componente{'\n'}100
              resultados por simulación
            </Text>
          </View>
          <Button
            label="Continuar con Google →"
            onPress={() => action(login)}
            disabled={busy}
          />
          <Text style={s.note}>
            Tus experimentos quedan asociados a tu cuenta.
          </Text>
          {error ? (
            <Text accessibilityRole="alert" style={s.error}>
              {error}
            </Text>
          ) : null}
        </ScrollView>
      </SafeAreaView>
    );
  return (
    <SafeAreaView style={s.root}>
      <StatusBar barStyle="dark-content" />
      <ScrollView
        keyboardShouldPersistTaps="handled"
        contentContainerStyle={s.container}
      >
        {header}
        <View style={s.row}>
          <Text numberOfLines={1} style={[s.note, { flex: 1 }]}>
            {user.displayName || user.email}
          </Text>
          <Pressable
            disabled={busy}
            accessibilityRole="button"
            onPress={() =>
              action(async () => {
                await signOut(getAuth());
                await GoogleSignin.signOut();
                setVars([]);
              })
            }
          >
            <Text style={s.link}>Salir</Text>
          </Pressable>
        </View>
        {page !== 'list' && (
          <Button
            label="← Mis experimentos"
            secondary
            disabled={busy}
            onPress={() => {
              setPage('list');
              setError('');
            }}
          />
        )}
        {error ? (
          <Text accessibilityRole="alert" style={s.error}>
            {error}
          </Text>
        ) : null}
        {busy && (
          <View style={s.row}>
            <ActivityIndicator color="#ad4a32" />
            <Text style={s.note}>Procesando... simulación hasta 60 s.</Text>
          </View>
        )}
        {page === 'list' && (
          <>
            <View style={s.row}>
              <Text style={s.h1}>Experimentos</Text>
              <Text style={s.counter}>{items.length}/10</Text>
            </View>
            <Button
              label="+ Nuevo experimento"
              disabled={
                busy ||
                !loaded ||
                items.length >= 10 ||
                !!usage?.running ||
                usage?.remaining === 0
              }
              onPress={() => {
                setVars([]);
                setExpressions(['X1 + X2']);
                setTitle('Mi experimento');
                setPage('new');
                setError('');
                pending.current = null;
              }}
            />
            <Text style={s.note}>
              Escenarios hoy (UTC): {usage?.used ?? '-'} / 25 · Reinicio 00:00
              UTC.{' '}
              {usage?.running
                ? 'Hay una simulación activa en tu cuenta. Actualiza cuando termine.'
                : ''}
            </Text>
            <Button
              label="Actualizar tabla"
              secondary
              disabled={busy}
              onPress={() => action(refresh)}
            />
            {items.length === 10 && (
              <Text style={s.note}>
                Llegaste al límite. Borra un experimento para crear otro.
              </Text>
            )}
            <View style={s.tableHead}>
              <Text style={[s.label, { flex: 1 }]}>NOMBRE / FECHA</Text>
              <Text style={s.label}>ACCIÓN</Text>
            </View>
            {loaded && !items.length && (
              <Text style={s.body}>
                Tu primera idea empieza aquí. Crea un experimento.
              </Text>
            )}
            {items.map((item, i) => (
              <View key={item.id} style={s.tableRow}>
                <View style={[s.dot, { backgroundColor: item.color }]} />
                <View style={{ flex: 1 }}>
                  <Text style={s.cardTitle}>
                    {String(i + 1).padStart(2, '0')} {item.title} ·{' '}
                    {item.dimensions || 1}D
                  </Text>
                  <Text style={s.note}>
                    {new Date(item.created_at).toLocaleString()}
                  </Text>
                </View>
                <View>
                  <Pressable
                    accessibilityRole="button"
                    disabled={busy}
                    onPress={() =>
                      action(async () => {
                        setDetail(await api<Experiment>('/' + item.id));
                        setBinText('10');
                        setPage('detail');
                      })
                    }
                  >
                    <Text style={s.link}>Abrir →</Text>
                  </Pressable>
                  <Pressable
                    accessibilityRole="button"
                    disabled={busy}
                    onPress={() => remove(item.id)}
                  >
                    <Text style={[s.link, { marginTop: 14 }]}>Borrar</Text>
                  </Pressable>
                </View>
              </View>
            ))}
          </>
        )}
        {page === 'new' && (
          <>
            <Text style={s.h1}>Nuevo experimento</Text>
            <Text style={s.note}>
              01 / DEFINE LAS VARIABLES ({vars.length}/
              {MAX_VARIABLES_PER_COMPONENT * expressions.length})
            </Text>
            {vars.map(v => (
              <View key={v.name} style={s.card}>
                <View style={s.row}>
                  <Text style={s.cardTitle}>
                    {v.name} /{' '}
                    {distributions.find(d => d.id === v.distribution)?.label}
                  </Text>
                  <Pressable
                    accessibilityRole="button"
                    onPress={() => setVars(vars.filter(x => x.name !== v.name))}
                  >
                    <Text style={s.link}>Quitar</Text>
                  </Pressable>
                </View>
                <Text style={s.note}>{describeVariable(v)}</Text>
                <Text style={s.note}>
                  Dominio: {v.domain?.min ?? '-∞'} a {v.domain?.max ?? '+∞'}
                </Text>
              </View>
            ))}
            {vars.length < MAX_VARIABLES_PER_COMPONENT * expressions.length && (
              <View style={s.card}>
                <Text style={s.label}>Distribución</Text>
                <Button
                  label={`${dist.label} · ${dist.kind} ▾`}
                  secondary
                  onPress={() => setPicker(true)}
                />
                <Text style={s.note}>{dist.help}</Text>
                {dist.fields.map(([key, label]) => (
                  <Field
                    key={key}
                    label={label}
                    value={fields[key] || ''}
                    onChange={text => setFields({ ...fields, [key]: text })}
                  />
                ))}
                <Text style={s.label}>
                  Dominio opcional (truncamiento inclusivo)
                </Text>
                <Field
                  label="Mínimo del dominio (vacío = sin límite)"
                  value={min}
                  onChange={setMin}
                />
                <Field
                  label="Máximo del dominio (vacío = sin límite)"
                  value={max}
                  onChange={setMax}
                />
                <Text style={s.note}>
                  Muestreo condicionado al intervalo, sin recortar valores.
                </Text>
                <Button label="Agregar variable" onPress={addVariable} />
              </View>
            )}
            <Text style={s.note}>
              02 / COMPONENTES: HASTA 5 VARIABLES DISTINTAS CADA UNO
            </Text>
            <Field
              label="Nombre del experimento"
              value={title}
              onChange={setTitle}
            />
            <View style={s.row}>
              {[1, 2, 3].map(d => (
                <Button
                  key={d}
                  label={`${d}D`}
                  secondary={expressions.length !== d}
                  disabled={busy}
                  onPress={() =>
                    setExpressions(old =>
                      Array.from({ length: d }, (_, i) => old[i] || 'X1'),
                    )
                  }
                />
              ))}
            </View>
            {expressions.map((expression, i) => (
              <Field
                key={i}
                label={`Componente ${
                  ['X', 'Y', 'Z'][i]
                }: expresión matemática (${
                  new Set(expression.match(/\bX\d+\b/g) || []).size
                }/5 variables)`}
                value={expression}
                onChange={text =>
                  setExpressions(old => old.map((v, j) => (i === j ? text : v)))
                }
                multiline
              />
            ))}
            <Text style={s.note}>
              + - * / ^ y paréntesis. Funciones: abs, sqrt, log (natural), exp,
              sin, cos. Ángulos en radianes. Ejemplo: X1 + 2*X2.
            </Text>
            <View style={s.card}>
              <Text style={s.cardTitle}>100 realizaciones conjuntas</Text>
              <Text style={s.body}>
                Hasta 5 variables distintas por componente, 15 en 3D. Variables
                base independientes. Cada realización evalúa todas las
                componentes con los mismos valores de las variables. Se guardan
                100 vectores ({expressions.length * 100} números), sin valores
                intermedios. Los componentes finales se truncan hacia cero a 3
                decimales antes de guardarse.
              </Text>
            </View>
            <Button
              label="Simular y guardar →"
              disabled={
                busy ||
                items.length >= 10 ||
                !!usage?.running ||
                usage?.remaining === 0
              }
              onPress={() => action(simulate)}
            />
          </>
        )}
        {page === 'detail' && detail && (
          <>
            <Text style={s.h1}>{detail.title}</Text>
            <Text selectable style={s.body}>
              {components(detail.spec)
                .map((e, i) => `${['X', 'Y', 'Z'][i]} = ${formatExpression(e)}`)
                .join('\n')}
            </Text>
            <Text style={s.note}>
              {new Date(detail.created_at).toLocaleString()} · 100 realizaciones
              · {components(detail.spec).length * 100} números
            </Text>
            {components(detail.spec).length === 1 ? (
              <Histogram
                experiment={detail}
                binText={binText}
                setBinText={setBinText}
              />
            ) : (
              <JointHistogram key={detail.id} experiment={detail} />
            )}
            <View style={s.card}>
              <Text style={s.cardTitle}>Definición del experimento</Text>
              {detail.spec.variables.map(v => (
                <Text key={v.name} style={s.note}>
                  {v.name}:{' '}
                  {distributions.find(d => d.id === v.distribution)?.label}
                  {'\n'}
                  {describeVariable(v)}
                  {'\n'}Dominio {v.domain?.min ?? '-∞'} a{' '}
                  {v.domain?.max ?? '+∞'}
                </Text>
              ))}
            </View>
            <Button
              label="Eliminar experimento"
              secondary
              disabled={busy}
              onPress={() => remove(detail.id)}
            />
          </>
        )}
      </ScrollView>
      <Modal
        visible={picker}
        animationType="slide"
        onRequestClose={() => setPicker(false)}
      >
        <SafeAreaView style={s.root}>
          <ScrollView contentContainerStyle={s.container}>
            <Text style={s.h1}>Elige una distribución</Text>
            {distributions.map(d => (
              <Button
                key={d.id}
                label={`${d.label} / ${d.kind}`}
                secondary
                onPress={() => {
                  setDist(d);
                  setFields(
                    Object.fromEntries(d.fields.map(([k, , v]) => [k, v])),
                  );
                  setPicker(false);
                }}
              />
            ))}
            <Button label="Cerrar" onPress={() => setPicker(false)} />
          </ScrollView>
        </SafeAreaView>
      </Modal>
    </SafeAreaView>
  );
}
function Histogram({
  experiment,
  binText,
  setBinText,
}: {
  experiment: Experiment;
  binText: string;
  setBinText: (s: string) => void;
}) {
  const bins = Number(binText),
    valid = Number.isInteger(bins) && bins >= 1 && bins <= 50;
  const h = histogram(experiment.results, valid ? bins : 10),
    peak = Math.max(...h.frequencies, 0.01),
    mean = experiment.results.reduce((a, b) => a + b, 0) / 100;
  return (
    <View style={s.card}>
      <Text style={s.cardTitle}>Frecuencia relativa</Text>
      <Field
        label="Número de particiones (1 a 50)"
        value={binText}
        onChange={setBinText}
      />
      {!valid && (
        <Text style={s.error}>
          Ingresa un entero de 1 a 50. Se muestran 10 mientras corriges.
        </Text>
      )}
      <Text style={s.note}>
        Escala vertical: 0 a {(peak * 100).toFixed(0)}%
      </Text>
      <View
        accessible
        accessibilityLabel={`Histograma de ${
          valid ? bins : 10
        } particiones y 100 resultados. Frecuencias relativas suman 100 por ciento.`}
        style={s.chart}
      >
        {h.frequencies.map((f, i) => (
          <View
            key={i}
            style={[
              s.bar,
              {
                height: `${(100 * f) / peak}%`,
                backgroundColor: experiment.color,
              },
            ]}
          />
        ))}
      </View>
      <View style={s.row}>
        <Text style={s.note}>{h.min.toPrecision(4)}</Text>
        <Text style={s.note}>{h.max.toPrecision(4)}</Text>
      </View>
      <Text style={s.note}>
        Cada barra = conteo / 100. Suma = 100%. Cambiar particiones no vuelve a
        simular.
      </Text>
      <Text style={s.body}>
        Media {mean.toPrecision(5)}
        {'\n'}Mín {Math.min(...experiment.results).toPrecision(5)} · Máx{' '}
        {Math.max(...experiment.results).toPrecision(5)}
      </Text>
      <Text style={s.label}>INTERVALO → FRECUENCIA</Text>
      {h.frequencies.map((f, i) => (
        <Text key={i} style={s.note}>
          [{(h.min + i * h.width).toPrecision(3)},{' '}
          {(h.min + (i + 1) * h.width).toPrecision(3)}
          {i === h.frequencies.length - 1 ? ']' : ')'} → {(100 * f).toFixed(0)}%
        </Text>
      ))}
    </View>
  );
}
export default function App() {
  return (
    <SafeAreaProvider>
      <AppContent />
    </SafeAreaProvider>
  );
}
const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#f5f1e7' },
  container: {
    padding: 24,
    paddingBottom: 60,
    maxWidth: 680,
    width: '100%',
    alignSelf: 'center',
  },
  header: {
    paddingTop: 20,
    paddingBottom: 24,
    borderBottomWidth: 1,
    borderColor: '#d2cdbf',
    marginBottom: 20,
  },
  eyebrow: {
    fontFamily: 'monospace',
    fontSize: 11,
    letterSpacing: 1.4,
    color: '#6d6b60',
  },
  brand: {
    fontFamily: 'monospace',
    fontWeight: 'bold',
    fontSize: 64,
    color: '#252d2a',
    letterSpacing: -5,
  },
  accent: { color: '#ad4a32' },
  subtitle: { fontFamily: 'monospace', fontSize: 12, color: '#64695e' },
  h1: {
    fontFamily: 'monospace',
    fontWeight: 'bold',
    fontSize: 25,
    color: '#252d2a',
    marginVertical: 20,
    flexShrink: 1,
  },
  body: {
    fontFamily: 'monospace',
    fontSize: 14,
    lineHeight: 23,
    color: '#39433b',
    marginVertical: 12,
  },
  note: {
    fontFamily: 'monospace',
    fontSize: 11,
    lineHeight: 18,
    color: '#65685b',
    marginVertical: 7,
  },
  label: {
    fontFamily: 'monospace',
    fontSize: 11,
    lineHeight: 17,
    color: '#52594c',
    marginBottom: 6,
  },
  card: {
    padding: 18,
    backgroundColor: '#eae7dc',
    borderRadius: 3,
    marginVertical: 14,
    borderWidth: 1,
    borderColor: '#d6d2c4',
  },
  cardTitle: {
    fontFamily: 'monospace',
    fontWeight: 'bold',
    fontSize: 14,
    color: '#293a30',
    flexShrink: 1,
  },
  button: {
    backgroundColor: '#2e493a',
    padding: 16,
    marginVertical: 8,
    borderRadius: 3,
    borderWidth: 1,
    borderColor: '#2e493a',
  },
  buttonText: {
    fontFamily: 'monospace',
    fontSize: 13,
    fontWeight: 'bold',
    color: '#fffaf0',
    textAlign: 'center',
  },
  secondary: { backgroundColor: 'transparent', borderColor: '#9a9d8e' },
  ink: { color: '#2e493a' },
  disabled: { opacity: 0.4 },
  field: { marginVertical: 9 },
  input: {
    fontFamily: 'monospace',
    fontSize: 14,
    color: '#252d2a',
    borderWidth: 1,
    borderColor: '#b3b4a5',
    padding: 12,
    borderRadius: 3,
    backgroundColor: '#faf8f0',
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 12,
    marginVertical: 6,
  },
  link: { fontFamily: 'monospace', fontSize: 12, color: '#963d28', padding: 5 },
  error: {
    fontFamily: 'monospace',
    fontSize: 12,
    lineHeight: 20,
    color: '#9d2f25',
    padding: 12,
    backgroundColor: '#f5dfd5',
    marginVertical: 12,
  },
  counter: { fontFamily: 'monospace', color: '#2e493a', fontSize: 18 },
  tableHead: {
    flexDirection: 'row',
    borderBottomWidth: 1,
    borderColor: '#9a9d8e',
    paddingVertical: 16,
    marginTop: 16,
  },
  tableRow: {
    flexDirection: 'row',
    gap: 12,
    alignItems: 'center',
    paddingVertical: 18,
    borderBottomWidth: 1,
    borderColor: '#d2cdbf',
  },
  dot: { height: 10, width: 10, borderRadius: 5 },
  chart: {
    height: 180,
    flexDirection: 'row',
    alignItems: 'flex-end',
    borderBottomWidth: 1,
    borderLeftWidth: 1,
    borderColor: '#79826f',
    gap: 2,
    marginTop: 10,
  },
  bar: { flex: 1, minHeight: 0 },
});
