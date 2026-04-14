import 'package:local_auth/local_auth.dart';

class AppSecurityService {
  final LocalAuthentication _auth = LocalAuthentication();

  Future<bool> canUseBiometrics() async {
    try {
      final supported = await _auth.isDeviceSupported();
      final canCheck = await _auth.canCheckBiometrics;
      return supported || canCheck;
    } catch (_) {
      return false;
    }
  }

  Future<bool> authenticateAdmin() async {
    try {
      return await _auth.authenticate(
        localizedReason: 'Confirme sua identidade para acessar o painel administrativo da NOVA.',
        options: const AuthenticationOptions(
          biometricOnly: false,
          stickyAuth: true,
          sensitiveTransaction: true,
        ),
      );
    } catch (_) {
      return false;
    }
  }
}
