class AnalysisResult {
  AnalysisResult({
    required this.generatedAt,
    required this.researchReference,
    required this.front,
    required this.side,
    required this.summary,
  });

  final String generatedAt;
  final String researchReference;
  final FaceViewResult front;
  final FaceViewResult side;
  final AnalysisSummary summary;

  factory AnalysisResult.fromJson(Map<String, dynamic> json) {
    return AnalysisResult(
      generatedAt: json['generated_at'] as String? ?? '',
      researchReference: json['research_reference'] as String? ?? '',
      front: FaceViewResult.fromJson(json['front'] as Map<String, dynamic>? ?? const {}),
      side: FaceViewResult.fromJson(json['side'] as Map<String, dynamic>? ?? const {}),
      summary: AnalysisSummary.fromJson(json['summary'] as Map<String, dynamic>? ?? const {}),
    );
  }
}

class FaceViewResult {
  FaceViewResult({
    required this.poseScore,
    required this.warnings,
    required this.groups,
    required this.supportedMetricCount,
  });

  final double poseScore;
  final List<String> warnings;
  final List<MetricGroup> groups;
  final int supportedMetricCount;

  factory FaceViewResult.fromJson(Map<String, dynamic> json) {
    final rawWarnings = json['warnings'] as List<dynamic>? ?? const [];
    final rawGroups = json['groups'] as List<dynamic>? ?? const [];

    return FaceViewResult(
      poseScore: (json['pose_score'] as num?)?.toDouble() ?? 0,
      warnings: rawWarnings.map((item) => item.toString()).toList(),
      groups: rawGroups
          .whereType<Map<String, dynamic>>()
          .map(MetricGroup.fromJson)
          .toList(),
      supportedMetricCount: json['supported_metric_count'] as int? ?? 0,
    );
  }
}

class MetricGroup {
  MetricGroup({
    required this.key,
    required this.label,
    required this.metrics,
  });

  final String key;
  final String label;
  final List<MetricValue> metrics;

  factory MetricGroup.fromJson(Map<String, dynamic> json) {
    final rawMetrics = json['metrics'] as List<dynamic>? ?? const [];
    return MetricGroup(
      key: json['key'] as String? ?? '',
      label: json['label'] as String? ?? '',
      metrics: rawMetrics
          .whereType<Map<String, dynamic>>()
          .map(MetricValue.fromJson)
          .toList(),
    );
  }
}

class MetricValue {
  MetricValue({
    required this.key,
    required this.label,
    required this.group,
    required this.view,
    required this.value,
    required this.unit,
    required this.formula,
    required this.idealMin,
    required this.idealMax,
    required this.interpretation,
    required this.notes,
    required this.status,
  });

  final String key;
  final String label;
  final String group;
  final String view;
  final double value;
  final String unit;
  final String formula;
  final double? idealMin;
  final double? idealMax;
  final String interpretation;
  final List<String> notes;
  final String status;

  factory MetricValue.fromJson(Map<String, dynamic> json) {
    final rawNotes = json['notes'] as List<dynamic>? ?? const [];
    return MetricValue(
      key: json['key'] as String? ?? '',
      label: json['label'] as String? ?? '',
      group: json['group'] as String? ?? '',
      view: json['view'] as String? ?? '',
      value: (json['value'] as num?)?.toDouble() ?? 0,
      unit: json['unit'] as String? ?? '',
      formula: json['formula'] as String? ?? '',
      idealMin: (json['ideal_min'] as num?)?.toDouble(),
      idealMax: (json['ideal_max'] as num?)?.toDouble(),
      interpretation: json['interpretation'] as String? ?? '',
      notes: rawNotes.map((item) => item.toString()).toList(),
      status: json['status'] as String? ?? 'no_reference',
    );
  }
}

class AnalysisSummary {
  AnalysisSummary({
    required this.supportedMetricCount,
    required this.unsupportedMetrics,
  });

  final int supportedMetricCount;
  final List<String> unsupportedMetrics;

  factory AnalysisSummary.fromJson(Map<String, dynamic> json) {
    final rawUnsupported = json['unsupported_metrics'] as List<dynamic>? ?? const [];
    return AnalysisSummary(
      supportedMetricCount: json['supported_metric_count'] as int? ?? 0,
      unsupportedMetrics: rawUnsupported.map((item) => item.toString()).toList(),
    );
  }
}
