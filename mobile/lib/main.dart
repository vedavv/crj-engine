import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import 'app.dart';
import 'services/api_client.dart';
import 'services/audio_service.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]);
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    statusBarIconBrightness: Brightness.light,
  ));

  runApp(
    MultiProvider(
      providers: [
        Provider(create: (_) => ApiClient(), dispose: (_, c) => c.dispose()),
        Provider(create: (_) => AudioService(), dispose: (_, s) => s.dispose()),
      ],
      child: const CrjSoundScapeApp(),
    ),
  );
}
