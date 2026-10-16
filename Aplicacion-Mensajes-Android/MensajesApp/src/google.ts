import { GoogleSignin, isErrorWithCode, isSuccessResponse, statusCodes } from '@react-native-google-signin/google-signin';
import { webClientId } from './api';

let configured = false;
export async function googleSignIn(): Promise<string | null> {
  if (!configured) { GoogleSignin.configure({ webClientId, offlineAccess: false }); configured = true; }
  try {
    await GoogleSignin.hasPlayServices({ showPlayServicesUpdateDialog: true });
    const result = await GoogleSignin.signIn();
    if (!isSuccessResponse(result)) return null;
    if (!result.data.idToken) throw new Error('Google no entregó un token. Revisa el cliente OAuth Web.');
    return result.data.idToken;
  } catch (error) {
    if (isErrorWithCode(error)) {
      if (error.code === statusCodes.SIGN_IN_CANCELLED || error.code === statusCodes.IN_PROGRESS) return null;
      if (error.code === statusCodes.PLAY_SERVICES_NOT_AVAILABLE) throw new Error('Actualiza Google Play Services para iniciar sesión.');
      throw new Error('No se pudo entrar con Google. Revisa los clientes OAuth y la huella SHA-1 de esta compilación.');
    }
    throw error;
  }
}
export async function googleSignOut() {
  if (!configured) { GoogleSignin.configure({ webClientId, offlineAccess: false }); configured = true; }
  await GoogleSignin.signOut();
}
