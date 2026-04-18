import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import 'models/analysis_result.dart';
import 'services/analysis_api.dart';
import 'widgets/metric_group_card.dart';

void main() {
  runApp(const FaceIqWindowsApp());
}

class FaceIqWindowsApp extends StatelessWidget {
  const FaceIqWindowsApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'FaceIQ Labs',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF0F766E),
          brightness: Brightness.light,
        ),
        scaffoldBackgroundColor: const Color(0xFFF6F1E8),
        textTheme: ThemeData.light().textTheme.apply(
              bodyColor: const Color(0xFF14213D),
              displayColor: const Color(0xFF14213D),
            ),
      ),
      home: const AnalyzerHomePage(),
    );
  }
}

class AnalyzerHomePage extends StatefulWidget {
  const AnalyzerHomePage({super.key});

  @override
  State<AnalyzerHomePage> createState() => _AnalyzerHomePageState();
}

class _AnalyzerHomePageState extends State<AnalyzerHomePage> {
  final TextEditingController _backendController = TextEditingController(
    text: 'http://127.0.0.1:8000',
  );

  String? _frontImagePath;
  String? _sideImagePath;
  bool _busy = false;
  String? _error;
  AnalysisResult? _result;

  @override
  void dispose() {
    _backendController.dispose();
    super.dispose();
  }

  Future<void> _pickImage({required bool front}) async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: const ['jpg', 'jpeg', 'png', 'webp'],
    );

    final path = result?.files.single.path;
    if (path == null) {
      return;
    }

    setState(() {
      if (front) {
        _frontImagePath = path;
      } else {
        _sideImagePath = path;
      }
    });
  }

  Future<void> _analyze() async {
    if (_frontImagePath == null || _sideImagePath == null) {
      setState(() {
        _error = 'Pick both a frontal photo and a side-profile photo before running analysis.';
      });
      return;
    }

    setState(() {
      _busy = true;
      _error = null;
    });

    try {
      final api = AnalysisApi(baseUrl: _backendController.text.trim());
      final result = await api.analyze(
        frontImagePath: _frontImagePath!,
        sideImagePath: _sideImagePath!,
      );

      setState(() {
        _result = result;
      });
    } on AnalysisApiException catch (exception) {
      setState(() {
        _error = exception.message;
      });
    } catch (exception) {
      setState(() {
        _error = 'Unexpected UI failure: $exception';
      });
    } finally {
      if (mounted) {
        setState(() {
          _busy = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              Color(0xFFF7EFE4),
              Color(0xFFE6F4F1),
              Color(0xFFF4E6E1),
            ],
          ),
        ),
        child: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(28),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _HeroBanner(
                  supportedMetricCount: _result?.summary.supportedMetricCount ?? 0,
                ),
                const SizedBox(height: 24),
                LayoutBuilder(
                  builder: (context, constraints) {
                    final compact = constraints.maxWidth < 1100;
                    if (compact) {
                      return Column(
                        children: [
                          _InputColumn(
                            backendController: _backendController,
                            frontImagePath: _frontImagePath,
                            sideImagePath: _sideImagePath,
                            busy: _busy,
                            onPickFront: () => _pickImage(front: true),
                            onPickSide: () => _pickImage(front: false),
                            onAnalyze: _analyze,
                          ),
                          const SizedBox(height: 24),
                          _ResultColumn(error: _error, result: _result),
                        ],
                      );
                    }

                    return Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        SizedBox(
                          width: 420,
                          child: _InputColumn(
                            backendController: _backendController,
                            frontImagePath: _frontImagePath,
                            sideImagePath: _sideImagePath,
                            busy: _busy,
                            onPickFront: () => _pickImage(front: true),
                            onPickSide: () => _pickImage(front: false),
                            onAnalyze: _analyze,
                          ),
                        ),
                        const SizedBox(width: 24),
                        Expanded(
                          child: _ResultColumn(error: _error, result: _result),
                        ),
                      ],
                    );
                  },
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _HeroBanner extends StatelessWidget {
  const _HeroBanner({required this.supportedMetricCount});

  final int supportedMetricCount;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(28),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(32),
        color: const Color(0xFF12355B),
        boxShadow: const [
          BoxShadow(
            color: Color(0x2212355B),
            blurRadius: 32,
            offset: Offset(0, 14),
          ),
        ],
      ),
      child: Wrap(
        spacing: 24,
        runSpacing: 18,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          SizedBox(
            width: 760,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'FaceIQ Labs Research Analyzer',
                  style: theme.textTheme.headlineMedium?.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.w800,
                    letterSpacing: -0.4,
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  'Upload one frontal photo and one side profile. The Python backend extracts landmarks and computes the frontal and lateral ratios described in research_Facial_Ratio.md.',
                  style: theme.textTheme.bodyLarge?.copyWith(
                    color: const Color(0xFFE2E8F0),
                    height: 1.5,
                  ),
                ),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
            decoration: BoxDecoration(
              color: const Color(0xFFECFDF5),
              borderRadius: BorderRadius.circular(24),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '$supportedMetricCount',
                  style: theme.textTheme.headlineMedium?.copyWith(
                    color: const Color(0xFF0F766E),
                    fontWeight: FontWeight.w800,
                  ),
                ),
                Text(
                  'metrics returned in the latest run',
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: const Color(0xFF285E61),
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _InputColumn extends StatelessWidget {
  const _InputColumn({
    required this.backendController,
    required this.frontImagePath,
    required this.sideImagePath,
    required this.busy,
    required this.onPickFront,
    required this.onPickSide,
    required this.onAnalyze,
  });

  final TextEditingController backendController;
  final String? frontImagePath;
  final String? sideImagePath;
  final bool busy;
  final VoidCallback onPickFront;
  final VoidCallback onPickSide;
  final VoidCallback onAnalyze;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        _ImagePickerCard(
          title: 'Frontal Photo',
          subtitle: 'Neutral expression, eyes level, full face visible.',
          imagePath: frontImagePath,
          accent: const Color(0xFFD1495B),
          buttonLabel: 'Choose front image',
          onPressed: onPickFront,
        ),
        const SizedBox(height: 18),
        _ImagePickerCard(
          title: 'Side Profile',
          subtitle: 'True side view with the forehead, nose, lips, and chin visible.',
          imagePath: sideImagePath,
          accent: const Color(0xFF1D7874),
          buttonLabel: 'Choose side image',
          onPressed: onPickSide,
        ),
        const SizedBox(height: 18),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(28),
            boxShadow: const [
              BoxShadow(
                color: Color(0x110F172A),
                blurRadius: 28,
                offset: Offset(0, 10),
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              TextField(
                controller: backendController,
                decoration: const InputDecoration(
                  labelText: 'Python backend URL',
                  hintText: 'http://127.0.0.1:8000',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 14),
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: busy ? null : onAnalyze,
                  icon: busy
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.analytics_outlined),
                  label: Text(busy ? 'Analyzing...' : 'Run FaceIQ analysis'),
                  style: FilledButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 18),
                    backgroundColor: const Color(0xFF12355B),
                    foregroundColor: Colors.white,
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _ImagePickerCard extends StatelessWidget {
  const _ImagePickerCard({
    required this.title,
    required this.subtitle,
    required this.imagePath,
    required this.accent,
    required this.buttonLabel,
    required this.onPressed,
  });

  final String title;
  final String subtitle;
  final String? imagePath;
  final Color accent;
  final String buttonLabel;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(28),
        border: Border.all(color: accent.withOpacity(0.15)),
        boxShadow: const [
          BoxShadow(
            color: Color(0x110F172A),
            blurRadius: 28,
            offset: Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: theme.textTheme.titleLarge?.copyWith(
              color: const Color(0xFF14213D),
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            subtitle,
            style: theme.textTheme.bodyMedium?.copyWith(
              color: const Color(0xFF526071),
            ),
          ),
          const SizedBox(height: 16),
          Container(
            height: 220,
            width: double.infinity,
            decoration: BoxDecoration(
              color: const Color(0xFFF8FAFC),
              borderRadius: BorderRadius.circular(22),
            ),
            clipBehavior: Clip.antiAlias,
            child: imagePath == null
                ? Center(
                    child: Icon(
                      Icons.add_photo_alternate_outlined,
                      size: 42,
                      color: accent,
                    ),
                  )
                : Image.file(
                    File(imagePath!),
                    fit: BoxFit.cover,
                    errorBuilder: (context, error, stackTrace) => Center(
                      child: Icon(
                        Icons.broken_image_outlined,
                        size: 42,
                        color: accent,
                      ),
                    ),
                  ),
          ),
          const SizedBox(height: 14),
          if (imagePath != null)
            Text(
              imagePath!,
              style: theme.textTheme.bodySmall?.copyWith(
                color: const Color(0xFF526071),
              ),
            ),
          const SizedBox(height: 14),
          OutlinedButton.icon(
            onPressed: onPressed,
            icon: const Icon(Icons.folder_open),
            label: Text(buttonLabel),
          ),
        ],
      ),
    );
  }
}

class _ResultColumn extends StatelessWidget {
  const _ResultColumn({
    required this.error,
    required this.result,
  });

  final String? error;
  final AnalysisResult? result;

  @override
  Widget build(BuildContext context) {
    if (error != null) {
      return _InfoPanel(
        title: 'Analysis error',
        body: error!,
        color: const Color(0xFFD1495B),
      );
    }

    if (result == null) {
      return const _InfoPanel(
        title: 'Waiting for analysis',
        body: 'Pick both photos, make sure the Python backend is running, then launch the analysis.',
        color: Color(0xFF1D7874),
      );
    }

    return Column(
      children: [
        _FaceViewPanel(
          title: 'Frontal Analysis',
          faceResult: result!.front,
          accent: const Color(0xFFD1495B),
        ),
        const SizedBox(height: 24),
        _FaceViewPanel(
          title: 'Side-Profile Analysis',
          faceResult: result!.side,
          accent: const Color(0xFF1D7874),
        ),
        const SizedBox(height: 24),
        _UnsupportedMetricsPanel(summary: result!.summary),
      ],
    );
  }
}

class _FaceViewPanel extends StatelessWidget {
  const _FaceViewPanel({
    required this.title,
    required this.faceResult,
    required this.accent,
  });

  final String title;
  final FaceViewResult faceResult;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Text(
              title,
              style: theme.textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.w800,
                color: const Color(0xFF14213D),
              ),
            ),
            const SizedBox(width: 12),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: accent.withOpacity(0.12),
                borderRadius: BorderRadius.circular(999),
              ),
              child: Text(
                'Pose score ${(faceResult.poseScore * 100).toStringAsFixed(0)}%',
                style: theme.textTheme.labelLarge?.copyWith(
                  color: accent,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
            const SizedBox(width: 12),
            Text(
              '${faceResult.supportedMetricCount} metrics',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: const Color(0xFF526071),
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
        if (faceResult.warnings.isNotEmpty) ...[
          const SizedBox(height: 14),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: const Color(0xFFFFF4E5),
              borderRadius: BorderRadius.circular(20),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: faceResult.warnings
                  .map(
                    (warning) => Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: Text(
                        '- $warning',
                        style: theme.textTheme.bodyMedium?.copyWith(
                          color: const Color(0xFF8A5B00),
                        ),
                      ),
                    ),
                  )
                  .toList(),
            ),
          ),
        ],
        const SizedBox(height: 18),
        for (final group in faceResult.groups) ...[
          MetricGroupCard(group: group, accentColor: accent),
          const SizedBox(height: 16),
        ],
      ],
    );
  }
}

class _UnsupportedMetricsPanel extends StatelessWidget {
  const _UnsupportedMetricsPanel({required this.summary});

  final AnalysisSummary summary;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(28),
        boxShadow: const [
          BoxShadow(
            color: Color(0x110F172A),
            blurRadius: 28,
            offset: Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Not Yet Implemented',
            style: theme.textTheme.titleLarge?.copyWith(
              fontWeight: FontWeight.w800,
              color: const Color(0xFF14213D),
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'These research items are still listed by the backend as unsupported because the guide marks them as inferred or they need landmarks that are unreliable in 2D without extra calibration.',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: const Color(0xFF526071),
              height: 1.5,
            ),
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: summary.unsupportedMetrics
                .map(
                  (metric) => Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                    decoration: BoxDecoration(
                      color: const Color(0xFFF1F5F9),
                      borderRadius: BorderRadius.circular(999),
                    ),
                    child: Text(
                      metric,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: const Color(0xFF475569),
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                )
                .toList(),
          ),
        ],
      ),
    );
  }
}

class _InfoPanel extends StatelessWidget {
  const _InfoPanel({
    required this.title,
    required this.body,
    required this.color,
  });

  final String title;
  final String body;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(28),
        border: Border.all(color: color.withOpacity(0.16)),
        boxShadow: const [
          BoxShadow(
            color: Color(0x110F172A),
            blurRadius: 28,
            offset: Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: theme.textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.w800,
              color: const Color(0xFF14213D),
            ),
          ),
          const SizedBox(height: 10),
          Text(
            body,
            style: theme.textTheme.bodyLarge?.copyWith(
              color: const Color(0xFF526071),
              height: 1.5,
            ),
          ),
        ],
      ),
    );
  }
}
