import React, { useState } from 'react';
import {
  requireNativeComponent,
  StyleSheet,
  Text,
  TextInput,
  View,
  Pressable,
  ViewProps,
} from 'react-native';
import { Experiment, components } from './api';
import { jointHistogram } from './jointHistogram';

type Props = ViewProps & {
  cells: number[][];
  dimensions: number;
  bins: number;
  ink: string;
  angle: number;
  maximum: number;
};
const NativeHistogram = requireNativeComponent<Props>('AzarJointHistogram');
const names = ['X', 'Y', 'Z'];
export default function JointHistogram({
  experiment,
}: {
  experiment: Experiment;
}) {
  const dimensions = components(experiment.spec).length;
  const limit = dimensions === 2 ? 12 : 8;
  const [text, setText] = useState('5'),
    [angle, setAngle] = useState(35),
    [slice, setSlice] = useState(-1);
  const n = Number(text),
    valid = Number.isInteger(n) && n >= 1 && n <= limit;
  const h = jointHistogram(experiment.results, dimensions, valid ? n : 5);
  const shown = h.cells.filter(c => slice < 0 || c.indices[2] === slice);
  const cellData = shown.map(c => [
    c.indices[0],
    c.indices[1],
    c.indices[2] || 0,
    c.frequency,
  ]);
  return (
    <View style={s.card}>
      <Text style={s.title}>Histograma conjunto {dimensions}D</Text>
      <Text style={s.text}>Particiones por eje (1 a {limit})</Text>
      <TextInput
        accessibilityLabel="Particiones por eje"
        style={s.input}
        value={text}
        keyboardType="number-pad"
        onChangeText={v => {
          setText(v);
          setSlice(-1);
        }}
      />
      {!valid && (
        <Text style={s.text}>
          Ingresa un entero de 1 a {limit}. Se muestran 5 mientras corriges.
        </Text>
      )}
      <NativeHistogram
        style={{ height: 320, width: '100%' }}
        cells={cellData}
        dimensions={dimensions}
        bins={h.bins}
        ink={experiment.color}
        angle={angle}
        maximum={h.peak}
        accessibilityLabel={`Histograma conjunto de ${dimensions} dimensiones. La tabla inferior contiene las frecuencias.`}
      />
      <View style={s.row}>
        <Pressable
          accessibilityRole="button"
          onPress={() => setAngle(a => (a - 15 + 360) % 360)}
        >
          <Text style={s.button}>↶ Girar</Text>
        </Pressable>
        <Pressable
          accessibilityRole="button"
          onPress={() => setAngle(a => (a + 15) % 360)}
        >
          <Text style={s.button}>Girar ↷</Text>
        </Pressable>
      </View>
      <Text style={s.text}>
        {dimensions === 2
          ? `Altura = frecuencia relativa. Máximo ${(100 * h.peak).toFixed(
              0,
            )}%.`
          : `X/Y/Z = componentes. Color más intenso = mayor frecuencia; máximo ${(
              100 * h.peak
            ).toFixed(0)}%.`}
      </Text>
      {dimensions === 3 && (
        <>
          <Text style={s.text}>Cortes de Z (sin renormalizar frecuencias)</Text>
          <View
            style={[s.row, { flexWrap: 'wrap', justifyContent: 'flex-start' }]}
          >
            {Array.from({ length: h.bins + 1 }, (_, i) => i - 1).map(i => (
              <Pressable
                key={i}
                accessibilityRole="button"
                onPress={() => setSlice(i)}
              >
                <Text
                  style={[
                    s.button,
                    slice === i && { backgroundColor: '#d4dccb' },
                  ]}
                >
                  {i < 0 ? 'Todo' : `Z${i + 1}`}
                </Text>
              </Pressable>
            ))}
          </View>
        </>
      )}
      {h.axes.map((a, d) => (
        <Text key={d} style={s.text}>
          {names[d]}: {a.min.toPrecision(4)} a {a.max.toPrecision(4)} · media{' '}
          {a.mean.toPrecision(4)}
        </Text>
      ))}
      <Text style={s.text}>
        Cada celda = conteo / 100. Todas suman 100%.{' '}
        {slice >= 0
          ? `Este corte suma ${(
              shown.reduce((sum, c) => sum + c.frequency, 0) * 100
            ).toFixed(0)}%.`
          : ''}{' '}
        Cambiar particiones o girar no vuelve a simular.
      </Text>
      <Text style={s.title}>Celdas ocupadas → frecuencia</Text>
      {shown.map(c => (
        <Text key={c.indices.join(',')} style={s.text}>
          {c.indices
            .map(
              (i, d) =>
                `${names[d]}${i + 1} [${(
                  h.axes[d].min +
                  i * h.axes[d].width
                ).toPrecision(3)}, ${(
                  h.axes[d].min +
                  (i + 1) * h.axes[d].width
                ).toPrecision(3)}${i === h.bins - 1 ? ']' : ')'}`,
            )
            .join(' / ')}{' '}
          → {(c.frequency * 100).toFixed(0)}%
        </Text>
      ))}
      <Text style={s.text}>
        Las celdas vacías tienen frecuencia 0%. Cien vectores,{' '}
        {dimensions * 100} números guardados.
      </Text>
    </View>
  );
}
const s = StyleSheet.create({
  card: {
    padding: 16,
    backgroundColor: '#eae7dc',
    marginVertical: 14,
    borderRadius: 3,
  },
  title: {
    fontFamily: 'monospace',
    fontWeight: 'bold',
    fontSize: 14,
    color: '#293a30',
    marginVertical: 10,
  },
  text: {
    fontFamily: 'monospace',
    fontSize: 11,
    lineHeight: 19,
    color: '#39433b',
    marginVertical: 6,
  },
  input: {
    fontFamily: 'monospace',
    padding: 12,
    borderWidth: 1,
    borderColor: '#b3b4a5',
    backgroundColor: '#faf8f0',
    color: '#252d2a',
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 8,
    marginVertical: 8,
  },
  button: {
    fontFamily: 'monospace',
    padding: 10,
    color: '#963d28',
    borderWidth: 1,
    borderColor: '#b3b4a5',
  },
});
