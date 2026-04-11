import 'package:flutter_test/flutter_test.dart';

import 'package:frontend_flutter/app.dart';

void main() {
  testWidgets('renderiza tela inicial da NOVA', (WidgetTester tester) async {
    await tester.pumpWidget(const NovaFrontendApp());
    expect(find.text('N.O.V.A'), findsOneWidget);
  });
}
