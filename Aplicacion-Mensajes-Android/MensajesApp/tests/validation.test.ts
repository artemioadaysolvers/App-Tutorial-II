import assert from 'node:assert/strict';
import test from 'node:test';
import { validateMessages } from '../src/validation.ts';

test('los tres campos son obligatorios y no aceptan solo espacios', () => {
  assert.equal(Object.keys(validateMessages({ mensaje1: '', mensaje2: '  ', mensaje3: '\n' })).length, 3);
});
test('acepta mensajes con caracteres españoles y hasta 2000 caracteres', () => {
  assert.deepEqual(validateMessages({ mensaje1: '¡Hola!', mensaje2: 'á'.repeat(2000), mensaje3: 'Gracias 😊' }), {});
});
test('rechaza mensajes demasiado largos', () => {
  assert.ok(validateMessages({ mensaje1: 'a'.repeat(2001), mensaje2: 'Hola', mensaje3: 'Adiós' }).mensaje1);
});
