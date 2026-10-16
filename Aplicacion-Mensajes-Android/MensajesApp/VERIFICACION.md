# Verificación de la entrega

Fecha de la entrega: 15 de octubre de 2026.

- React Native 0.88.0, React 19.3.0 y Expo SDK 58, resueltos con `package-lock.json`.
- TypeScript: `npm run typecheck`, correcto.
- Validación de campos: `npm test`, 3 pruebas aprobadas.
- Proyecto Android: generado con `expo prebuild --platform android --no-install`.
- Empaquetado Android: `npm run check:bundle`, correcto; se generó bytecode Hermes.
- Compatibilidad: dependencias contrastadas con las versiones incluidas en el SDK de Expo; comprobación CLI en modo offline correcta.
- Workflow de GitHub: validado con actionlint.

No se generó ni instaló un APK y no se comprobó el login con una cuenta real. Para completar la prueba en Android, configura la URL de la API, los clientes OAuth y la huella SHA-1 y compila siguiendo README.md.

El ZIP no incluye node_modules, archivos .env reales, credenciales de producción ni el bundle de comprobación. La firma debug.keystore incluida es la firma pública de desarrollo del proyecto Android y solo sirve para pruebas.
