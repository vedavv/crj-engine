import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

import 'package:crj_soundscape/app.dart';
import 'package:crj_soundscape/services/api_client.dart';
import 'package:crj_soundscape/services/audio_service.dart';

void main() {
  testWidgets('App launches with splash screen', (WidgetTester tester) async {
    await tester.pumpWidget(
      MultiProvider(
        providers: [
          Provider(create: (_) => ApiClient()),
          Provider(create: (_) => AudioService()),
        ],
        child: const CrjSoundScapeApp(),
      ),
    );

    expect(find.text('CRJ SOUNDSCAPE'), findsOneWidget);
    expect(find.text('SACRED AUDIO ANALYSIS'), findsOneWidget);
  });
}
