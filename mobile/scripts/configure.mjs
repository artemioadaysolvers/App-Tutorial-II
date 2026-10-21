import fs from 'node:fs';
const apiUrl = process.argv[2]?.replace(/\/$/, '');
if (!apiUrl || !/^https:\/\/[^\s]+$/.test(apiUrl))
  throw Error('Uso: npm run configure -- https://TU-SERVICIO.run.app');
const json = JSON.parse(
  fs.readFileSync('android/app/google-services.json', 'utf8'),
);
const client = json.client.find(
  c => c.client_info.android_client_info.package_name === 'com.montecarlolab',
);
const webClientId = client?.oauth_client?.find(
  c => c.client_type === 3,
)?.client_id;
if (!webClientId)
  throw Error(
    'Falta cliente OAuth Web tipo 3. Habilita Google Auth, agrega SHA-1 y descarga de nuevo google-services.json para com.montecarlolab.',
  );
fs.writeFileSync(
  'src/config.ts',
  `export const config = ${JSON.stringify(
    { configured: true, apiUrl, webClientId },
    null,
    2,
  )};\n`,
);
console.log('Configuración generada. Vuelve a compilar la app.');
