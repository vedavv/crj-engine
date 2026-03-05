import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../theme/soundscape_theme.dart';
import 'home_screen.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;
  late final Animation<double> _fadeIn;
  late final Animation<double> _glowPulse;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2500),
    );
    _fadeIn = CurvedAnimation(parent: _ctrl, curve: Curves.easeIn);
    _glowPulse = Tween(begin: 0.4, end: 1.0).animate(
      CurvedAnimation(parent: _ctrl, curve: Curves.easeInOut),
    );
    _ctrl.forward();

    Future.delayed(const Duration(seconds: 3), () {
      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        PageRouteBuilder(
          pageBuilder: (context, animation, secondaryAnimation) =>
              const HomeScreen(),
          transitionsBuilder: (context, a, secondaryAnimation, child) =>
              FadeTransition(opacity: a, child: child),
          transitionDuration: const Duration(milliseconds: 800),
        ),
      );
    });
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: RadialGradient(
            center: Alignment.center,
            radius: 1.2,
            colors: [
              Color(0xFF1A0F2E),
              SoundScapeTheme.deepSacred,
            ],
          ),
        ),
        child: Center(
          child: FadeTransition(
            opacity: _fadeIn,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                // Emblem with golden glow
                AnimatedBuilder(
                  animation: _glowPulse,
                  builder: (context, child) => Container(
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      boxShadow: [
                        BoxShadow(
                          color: SoundScapeTheme.amberGlow
                              .withValues(alpha: _glowPulse.value * 0.5),
                          blurRadius: 60,
                          spreadRadius: 20,
                        ),
                        BoxShadow(
                          color: SoundScapeTheme.sacredSaffron
                              .withValues(alpha: _glowPulse.value * 0.3),
                          blurRadius: 100,
                          spreadRadius: 40,
                        ),
                      ],
                    ),
                    child: child,
                  ),
                  child: ClipOval(
                    child: Image.asset(
                      'assets/images/crj-emblem.jpg',
                      width: 160,
                      height: 160,
                      fit: BoxFit.cover,
                    ),
                  ),
                ),
                const SizedBox(height: 40),
                // Title
                Text(
                  'CRJ SOUNDSCAPE',
                  style: GoogleFonts.cinzel(
                    fontSize: 22,
                    letterSpacing: 6,
                    color: SoundScapeTheme.amberGlow,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  'SACRED AUDIO ANALYSIS',
                  style: GoogleFonts.cinzel(
                    fontSize: 10,
                    letterSpacing: 4,
                    color: SoundScapeTheme.textMuted,
                    fontWeight: FontWeight.w400,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
