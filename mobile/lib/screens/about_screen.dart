import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../theme/soundscape_theme.dart';

class AboutScreen extends StatelessWidget {
  const AboutScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('ABOUT')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          // Hero
          Center(
            child: Column(
              children: [
                ClipRRect(
                  borderRadius: BorderRadius.circular(16),
                  child: Image.asset(
                    'assets/images/crj-emblem.jpg',
                    width: 100,
                    height: 100,
                    fit: BoxFit.cover,
                  ),
                ),
                const SizedBox(height: 16),
                Text(
                  'CRJ SOUNDSCAPE',
                  style: GoogleFonts.cinzel(
                    fontSize: 22,
                    letterSpacing: 3,
                    color: SoundScapeTheme.amberGlow,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'CREATE  •  REFINE  •  JUBILATE',
                  style: GoogleFonts.cinzel(
                    fontSize: 10,
                    letterSpacing: 2,
                    color: SoundScapeTheme.textMuted,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  'गायत्री छन्दसामहम्',
                  style: GoogleFonts.cormorantGaramond(
                    fontSize: 16,
                    color: SoundScapeTheme.amberGlow,
                  ),
                ),
                Text(
                  '— श्रीमद्भगवद्गीता १०.३५',
                  style: GoogleFonts.cormorantGaramond(
                    fontSize: 12,
                    color: SoundScapeTheme.textMuted,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 32),

          // About the App
          _sectionTitle('ABOUT THE APP'),
          const SizedBox(height: 12),
          _bodyText(
            'CRJ SoundScape is a sacred audio analysis and composition platform '
            'for Indian classical music. It combines AI-powered pitch detection, '
            'swara mapping, raga identification, gamaka classification, and audio '
            'synthesis — purpose-built for Carnatic music study, practice, and '
            'the preservation of Vedic oral traditions.',
          ),
          const SizedBox(height: 8),
          _bodyText(
            'All notation is rendered in five scripts — IAST (Roman), Devanāgarī, '
            'Kannaḍa, Tamil, and Telugu.',
          ),
          const SizedBox(height: 20),

          // Features
          _sectionTitle('FEATURES'),
          const SizedBox(height: 12),
          _featureRow(Icons.music_note_rounded, 'Sacred Audio Player',
              'Curated Sāmaveda Setu recitations with waveform visualisation'),
          _featureRow(Icons.graphic_eq_rounded, 'Swara Analysis',
              'AI pitch detection (CREPE & pYIN) mapping to 12 swarasthānas'),
          _featureRow(Icons.piano_rounded, 'Composition Tool',
              'Notation input, instruments, tāla patterns, shruti drone'),
          _featureRow(Icons.search_rounded, 'Raga Identification',
              'Classify melodic framework from swara sequences'),
          _featureRow(Icons.translate_rounded, 'Multilingual Output',
              'IAST, Devanāgarī, Kannaḍa, Tamil, Telugu with PDF export'),
          _featureRow(Icons.timer_rounded, '35 Suladi Sapta Tālas',
              '7 base patterns × 5 jātis for composition and practice'),
          const SizedBox(height: 24),

          // About the Creator
          _sectionTitle('ABOUT THE CREATOR'),
          const SizedBox(height: 12),
          _card(
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Dr. Vamśīkṛṣṇa Ghanapāṭhī',
                  style: GoogleFonts.cinzel(
                    fontSize: 16,
                    color: SoundScapeTheme.amberGlow,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'वेदनिधिः  •  वाचस्पतिः  •  ಡಾ. ವಂಶೀಕೃಷ್ಣ ಘನಪಾಠೀ',
                  style: GoogleFonts.cormorantGaramond(
                    fontSize: 14,
                    color: SoundScapeTheme.textMuted,
                  ),
                ),
                const SizedBox(height: 14),
                _bodyText(
                  'Dr. Vamśīkṛṣṇa Ghanapāṭhī is a Yajurveda Ghanapāṭhī, '
                  'Chaturvedī, author, and Sanskrit scholar based in Mysore, India. '
                  'He is the Founder of CRJ Studio and Director of SVAMI '
                  '(Saṁskṛta Veda Adhyayana Mandira Institute). He is also the '
                  'founder and guiding force behind Veda Vijñāna Viśtāram '
                  '(vedavishtaram.in) — an Institution of Eminence dedicated to '
                  'Vedic education, research, and the preservation of India\'s oral '
                  'scholarly traditions.',
                ),
                _bodyText(
                  'His vision bridges ancient Vedic knowledge with modern technology. '
                  'Under his guidance, CRJ Studio was established to digitize, analyze, '
                  'and propagate sacred audio traditions — ensuring the precision of '
                  'Vedic recitation and Indian classical music is preserved for future '
                  'generations through AI-powered tools.',
                ),
              ],
            ),
            highlight: true,
          ),
          const SizedBox(height: 16),

          // Honors
          _sectionTitle('HONORS & TITLES'),
          const SizedBox(height: 12),
          _honorRow('Vedanidhi (वेदनिधिः)', 'Treasury of Vedic Knowledge'),
          _honorRow('Vāchaspati (वाचस्पतिः)', 'Master of Sacred Speech'),
          _honorRow('Yajurveda Ghanapāṭhī', 'Master of Ghanapāṭha recitation'),
          _honorRow('Chaturvedī', 'Scholar of all four Vedas'),
          _honorRow('Founder', 'CRJ Studio, Mysore'),
          _honorRow('Author', ''),
          _honorRow('Director', 'SVAMI (Saṁskṛta Veda Adhyayana Mandira Institute)'),
          const SizedBox(height: 24),

          // CRJ Studio
          _sectionTitle('CRJ STUDIO — MYSORE'),
          const SizedBox(height: 12),
          _bodyText(
            'CRJ Studio is the technical and creative wing of Veda Vijñāna '
            'Viśtāram, delivering professional services across audio production, '
            'app development, multimedia, and scholarly training.',
          ),
          const SizedBox(height: 12),
          _serviceRow('Audio Division',
              'Recording and mastering of mantras, pūjā, and classical music. '
              'Noise restoration, multi-track mixing, and archival mastering.'),
          _serviceRow('App Development',
              'AI-driven applications including CRJ SoundScape and the Mahaan App '
              'for spiritual communities.'),
          _serviceRow('Multimedia',
              'Video production for rituals, cultural events, scholarly debates, '
              'and lecture demonstrations.'),
          _serviceRow('Training',
              'Internships for young scholars, digital content creation training, '
              'multilingual public speaker development.'),
          const SizedBox(height: 24),

          // Veda Vijnana Vishtaram
          _sectionTitle('VEDA VIJÑĀNA VIŚTĀRAM'),
          const SizedBox(height: 12),
          _bodyText(
            'An Institution of Eminence for learning Veda, Vedāṅga, and Vedic '
            'Philosophy, operating as a unit of Sanātana Guru Sampradāya '
            'Pratiṣṭhānam. Schools for all four Vedas — Rigveda, Yajurveda, '
            'Sāmaveda, and Atharvaveda — alongside programs in Sanskrit, '
            'Jyotiṣa, Vyākaraṇa, and ritual studies.',
          ),
          const SizedBox(height: 24),

          // Contact
          _sectionTitle('CONTACT'),
          const SizedBox(height: 12),
          _card(
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _contactRow('ADDRESS',
                    '114 Ānanda Ghanam, Gundurao Nagara\nMysore 570025, Karnataka, India'),
                const Divider(color: SoundScapeTheme.cardBorder, height: 24),
                _contactRow('EMAIL', 'crj@vedavishtaram.in'),
                const Divider(color: SoundScapeTheme.cardBorder, height: 24),
                _contactRow('WHATSAPP', '+91 99000 82065'),
                const Divider(color: SoundScapeTheme.cardBorder, height: 24),
                _contactRow('WEB', 'vedavishtaram.in  •  vedavishtaram.in/crj'),
              ],
            ),
          ),
          const SizedBox(height: 32),

          // Dedication
          Center(
            child: Column(
              children: [
                Container(
                  width: 40,
                  height: 1,
                  color: SoundScapeTheme.amberGlow.withAlpha(80),
                ),
                const SizedBox(height: 16),
                Text(
                  'Curated in loving memory of',
                  style: GoogleFonts.cormorantGaramond(
                    fontSize: 14,
                    fontStyle: FontStyle.italic,
                    color: SoundScapeTheme.textMuted,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'श्री चागण्टि रामयोगेश्वर राव',
                  style: GoogleFonts.cormorantGaramond(
                    fontSize: 16,
                    color: SoundScapeTheme.amberGlow,
                  ),
                ),
                const SizedBox(height: 24),
              ],
            ),
          ),

          // Footer
          Center(
            child: Text(
              '© 2026 CRJ Studio, Mysore',
              style: GoogleFonts.cinzel(
                fontSize: 10,
                color: SoundScapeTheme.textMuted,
                letterSpacing: 1,
              ),
            ),
          ),
          const SizedBox(height: 20),
        ],
      ),
    );
  }

  // --- Helpers ---

  static Widget _sectionTitle(String text) => Text(
        text,
        style: GoogleFonts.cinzel(
          fontSize: 11,
          letterSpacing: 2,
          color: SoundScapeTheme.amberGlow,
          fontWeight: FontWeight.w600,
        ),
      );

  static Widget _bodyText(String text) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Text(
          text,
          style: GoogleFonts.cormorantGaramond(
            fontSize: 15,
            height: 1.7,
            color: SoundScapeTheme.textLight,
          ),
        ),
      );

  static Widget _card(Widget child, {bool highlight = false}) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          color: SoundScapeTheme.cardBg,
          borderRadius: BorderRadius.circular(8),
          border: Border(
            left: BorderSide(
              color: highlight
                  ? SoundScapeTheme.amberGlow
                  : SoundScapeTheme.cardBorder,
              width: highlight ? 3 : 1,
            ),
            top: BorderSide(color: SoundScapeTheme.cardBorder, width: 1),
            right: BorderSide(color: SoundScapeTheme.cardBorder, width: 1),
            bottom: BorderSide(color: SoundScapeTheme.cardBorder, width: 1),
          ),
        ),
        child: child,
      );

  static Widget _featureRow(IconData icon, String title, String desc) =>
      Padding(
        padding: const EdgeInsets.only(bottom: 14),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: SoundScapeTheme.amberGlow, size: 20),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: GoogleFonts.cinzel(
                      fontSize: 12,
                      color: SoundScapeTheme.textLight,
                      letterSpacing: 0.5,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    desc,
                    style: GoogleFonts.cormorantGaramond(
                      fontSize: 14,
                      color: SoundScapeTheme.textMuted,
                      height: 1.5,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      );

  static Widget _honorRow(String title, String desc) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('✦ ',
                style: TextStyle(color: SoundScapeTheme.amberGlow, fontSize: 12)),
            Expanded(
              child: RichText(
                text: TextSpan(
                  children: [
                    TextSpan(
                      text: title,
                      style: GoogleFonts.cormorantGaramond(
                        fontSize: 15,
                        color: SoundScapeTheme.textLight,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    if (desc.isNotEmpty) TextSpan(
                      text: ' — $desc',
                      style: GoogleFonts.cormorantGaramond(
                        fontSize: 15,
                        color: SoundScapeTheme.textMuted,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      );

  static Widget _serviceRow(String title, String desc) => Container(
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.only(left: 14, top: 8, bottom: 8),
        decoration: const BoxDecoration(
          border: Border(
            left: BorderSide(
              color: SoundScapeTheme.cardBorder,
              width: 2,
            ),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: GoogleFonts.cinzel(
                fontSize: 12,
                color: SoundScapeTheme.amberGlow,
                letterSpacing: 0.5,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              desc,
              style: GoogleFonts.cormorantGaramond(
                fontSize: 14,
                color: SoundScapeTheme.textMuted,
                height: 1.5,
              ),
            ),
          ],
        ),
      );

  static Widget _contactRow(String label, String value) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: GoogleFonts.cinzel(
              fontSize: 9,
              letterSpacing: 1.5,
              color: SoundScapeTheme.amberGlow,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            value,
            style: GoogleFonts.cormorantGaramond(
              fontSize: 14,
              color: SoundScapeTheme.textLight,
              height: 1.5,
            ),
          ),
        ],
      );
}
