import React, { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Alert, KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, TextInput, View } from 'react-native';
import { GoogleSigninButton } from '@react-native-google-signin/google-signin';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';
import * as SecureStore from 'expo-secure-store';
import * as Crypto from 'expo-crypto';
import { ApiError, configurationIssue, getMe, sendMessages, signInApi } from './src/api';
import { googleSignIn, googleSignOut } from './src/google';
import type { Messages, Session } from './src/types';
import { fields, MAX_MESSAGE_LENGTH, validateMessages } from './src/validation';
import type { MessageKey } from './src/validation';
import { styles as s } from './src/styles';

const SESSION_KEY = 'mensajes.session.v1';
const empty: Messages = { mensaje1: '', mensaje2: '', mensaje3: '' };

function AppContent() {
  const [session, setSession] = useState<Session | null>(null);
  const [restoring, setRestoring] = useState(true);
  const [signingIn, setSigningIn] = useState(false);
  const [sending, setSending] = useState(false);
  const [values, setValues] = useState<Messages>(empty);
  const [errors, setErrors] = useState<Partial<Record<MessageKey, string>>>({});
  const [notice, setNotice] = useState<string | null>(null);
  const [lastSaved, setLastSaved] = useState<string | null>(null);
  const requestId = useRef<string | null>(null);
  const draftOwner = useRef<string | null>(null);
  const inputs = useRef<Partial<Record<MessageKey, { focus: () => void } | null>>>({});
  const configIssue = configurationIssue();

  useEffect(() => {
    let active = true;
    async function restore() {
      try {
        const raw = await SecureStore.getItemAsync(SESSION_KEY);
        if (!raw || configIssue) return;
        const saved = JSON.parse(raw) as Session;
        if (!saved.accessToken || !(new Date(saved.expiresAt).getTime() > Date.now() + 30000)) {
          await SecureStore.deleteItemAsync(SESSION_KEY);
          return;
        }
        const user = await getMe(saved.accessToken);
        if (active) { setSession({ ...saved, user }); draftOwner.current = user.id; }
      } catch (error) {
        if (!(error instanceof ApiError) || error.status === 401) {
          await SecureStore.deleteItemAsync(SESSION_KEY).catch(() => undefined);
        }
        if (active) setNotice('Vuelve a entrar con Google para continuar.');
      } finally { if (active) setRestoring(false); }
    }
    void restore();
    return () => { active = false; };
  }, [configIssue]);

  async function login() {
    if (signingIn || configIssue) return;
    setSigningIn(true); setNotice(null);
    try {
      const idToken = await googleSignIn();
      if (!idToken) return;
      const next = await signInApi(idToken);
      await SecureStore.setItemAsync(SESSION_KEY, JSON.stringify(next));
      if (draftOwner.current && draftOwner.current !== next.user.id) {
        setValues(empty); setErrors({}); requestId.current = null;
      }
      draftOwner.current = next.user.id;
      setSession(next);
    } catch (error) { setNotice(error instanceof Error ? error.message : 'No se pudo iniciar sesión.'); }
    finally { setSigningIn(false); }
  }

  async function logout(clearDraft = true) {
    await SecureStore.deleteItemAsync(SESSION_KEY);
    await googleSignOut().catch(() => undefined);
    setSession(null); setLastSaved(null); setNotice(null);
    if (clearDraft) {
      setValues(empty); setErrors({}); requestId.current = null; draftOwner.current = null;
    }
  }

  async function submit() {
    if (!session || sending) return;
    const nextErrors = validateMessages(values);
    setErrors(nextErrors);
    const firstError = fields.find(field => nextErrors[field]);
    if (firstError) { inputs.current[firstError]?.focus(); return; }
    if (new Date(session.expiresAt).getTime() <= Date.now()) {
      await logout(false);
      setNotice('Tu sesión venció. Entra de nuevo para enviar lo que escribiste.');
      return;
    }
    setSending(true); setNotice(null);
    requestId.current ??= Crypto.randomUUID();
    try {
      const trimmed = { mensaje1: values.mensaje1.trim(), mensaje2: values.mensaje2.trim(), mensaje3: values.mensaje3.trim() };
      const result = await sendMessages(session.accessToken, requestId.current, trimmed);
      setLastSaved(result.id); setValues(empty); setErrors({}); requestId.current = null;
      Alert.alert('Mensajes enviados', 'Tus tres mensajes se guardaron correctamente.');
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        await logout(false);
        setNotice('Tu sesión venció. Entra con Google para enviar tus mensajes.');
      } else setNotice(error instanceof Error ? error.message : 'No pudimos guardar los mensajes.');
    } finally { setSending(false); }
  }

  if (restoring) return <View style={s.loader}><ActivityIndicator size="large" color="#136C60" /><Text style={s.muted}>Abriendo tu espacio…</Text></View>;

  return <SafeAreaView style={s.safe}>
    <StatusBar style="dark" />
    <KeyboardAvoidingView style={s.flex} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView contentContainerStyle={s.page} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>
        <View style={s.topbar}>
          <View style={s.brand}><View style={s.logo}><Text style={s.logoText}>m</Text></View><Text style={s.brandText}>mensajes</Text></View>
          {session ? <Pressable accessibilityRole="button" disabled={sending} hitSlop={12} onPress={() => void logout().catch(() => setNotice('No se pudo cerrar la sesión. Inténtalo de nuevo.'))}><Text style={s.logout}>Salir</Text></Pressable> : <Text style={s.topLabel}>TU ESPACIO</Text>}
        </View>
        {!session ? <>
          <View style={s.hero}><Text style={s.eyebrow}>CONECTA. ESCRIBE. ENVÍA.</Text><Text style={s.title}>{'Tus ideas,\nen un solo lugar.'}</Text><Text style={s.intro}>Un espacio sencillo para compartir tus mensajes. Entra con tu cuenta de Google y empieza a escribir.</Text></View>
          <View style={s.illustration} accessible={false}>
            <View style={s.note}><View style={s.noteHeader}><View style={s.noteDot} /><Text style={s.noteTitle}>Un nuevo mensaje</Text></View><View style={s.noteLine} /><View style={[s.noteLine, { width: '78%' }]} /><View style={[s.noteLine, { width: '52%' }]} /><View style={s.noteBadge}><Text style={s.noteBadgeText}>Listo para compartir ↗</Text></View></View>
            <View style={s.floatBadge}><Text style={s.floatBadgeText}>✓</Text></View>
          </View>
          <View style={s.card}>
            <Text style={s.cardTitle}>Bienvenido a tu espacio</Text><Text style={s.cardDescription}>Continúa con tu cuenta para enviar tus mensajes.</Text>
            <GoogleSigninButton style={s.googleButton} size={GoogleSigninButton.Size.Wide} color={GoogleSigninButton.Color.Light} disabled={signingIn || Boolean(configIssue)} onPress={() => void login()} />
            {signingIn && <View style={s.loginProgress}><ActivityIndicator color="#136C60" /><Text style={s.muted}>Conectando…</Text></View>}
            <Text style={s.smallPrint}>Usaremos tu nombre y correo para identificar tus envíos.</Text>
          </View>
        </> : <>
          <View style={s.profile}><View style={s.avatar}><Text style={s.avatarText}>{(session.user.name || session.user.email).slice(0, 1).toUpperCase()}</Text></View><View style={s.profileInfo}><Text style={s.profileName} numberOfLines={1}>{session.user.name}</Text><Text style={s.profileEmail} numberOfLines={1}>{session.user.email}</Text></View><View style={s.onlineDot} /></View>
          <View style={s.formHero}><Text style={s.eyebrow}>DALE FORMA A TUS IDEAS</Text><Text style={s.formTitle}>{'¿Qué quieres\ncompartir hoy?'}</Text><Text style={s.formDescription}>Completa los tres mensajes y envíalos juntos.</Text></View>
          {lastSaved && <View style={s.success} accessibilityLiveRegion="polite"><Text style={s.successTitle}>✓  Envío guardado</Text><Text style={s.successText}>Puedes escribir tres mensajes nuevos.</Text></View>}
          <View style={s.formCard}>
            {fields.map((field, index) => <View key={field} style={s.field}>
              <View style={s.fieldHeader}><Text style={s.label}>Mensaje {index + 1}</Text><Text style={s.counter}>{values[field].length}/{MAX_MESSAGE_LENGTH}</Text></View>
              <TextInput ref={input => { inputs.current[field] = input; }} accessibilityLabel={`Mensaje ${index + 1}`} accessibilityHint="Campo obligatorio, hasta dos mil caracteres" value={values[field]} multiline textAlignVertical="top" editable={!sending} maxLength={MAX_MESSAGE_LENGTH} placeholder={['Escribe tu primer mensaje…', 'Continúa con tu segundo mensaje…', 'Añade tu tercer mensaje…'][index]} placeholderTextColor="#8A9792" onChangeText={text => { setValues(current => ({ ...current, [field]: text })); setErrors(current => ({ ...current, [field]: undefined })); requestId.current = null; setLastSaved(null); }} style={[s.input, errors[field] && s.inputError]} />
              {errors[field] && <Text style={s.fieldError}>{errors[field]}</Text>}
            </View>)}
            <Pressable accessibilityRole="button" disabled={sending} onPress={() => void submit().catch(() => setNotice('No se pudo completar la operación. Inténtalo de nuevo.'))} style={({ pressed }) => [s.sendButton, sending && s.disabled, pressed && s.pressed]}>{sending && <ActivityIndicator color="#FFF" />}<Text style={s.sendButtonText}>{sending ? 'Guardando mensajes…' : 'Enviar mensajes'}</Text>{!sending && <Text style={s.sendArrow}>↗</Text>}</Pressable>
            <Text style={s.saveHint}>Tus mensajes quedan asociados a tu cuenta.</Text>
          </View>
        </>}
        {(configIssue || notice) && <View style={s.errorBox} accessibilityRole="alert" accessibilityLiveRegion="polite"><Text style={s.errorText}>{configIssue || notice}</Text></View>}
        <Text style={s.footer}>Un espacio para lo que quieres decir.</Text>
      </ScrollView>
    </KeyboardAvoidingView>
  </SafeAreaView>;
}

export default function App() { return <SafeAreaProvider><AppContent /></SafeAreaProvider>; }
