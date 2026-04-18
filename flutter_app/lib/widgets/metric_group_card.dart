import 'package:flutter/material.dart';

import '../models/analysis_result.dart';

class MetricGroupCard extends StatelessWidget {
  const MetricGroupCard({
    super.key,
    required this.group,
    required this.accentColor,
  });

  final MetricGroup group;
  final Color accentColor;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(28),
        border: Border.all(color: accentColor.withOpacity(0.18)),
        boxShadow: const [
          BoxShadow(
            color: Color(0x110F172A),
            blurRadius: 28,
            offset: Offset(0, 10),
          ),
        ],
      ),
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 12,
                height: 12,
                decoration: BoxDecoration(
                  color: accentColor,
                  shape: BoxShape.circle,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  group.label,
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w700,
                    color: const Color(0xFF14213D),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 18),
          for (var index = 0; index < group.metrics.length; index++) ...[
            _MetricRow(metric: group.metrics[index]),
            if (index != group.metrics.length - 1)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 14),
                child: Divider(height: 1),
              ),
          ],
        ],
      ),
    );
  }
}

class _MetricRow extends StatelessWidget {
  const _MetricRow({required this.metric});

  final MetricValue metric;

  Color _statusColor() {
    switch (metric.status) {
      case 'within_ideal':
        return const Color(0xFF2A9D8F);
      case 'below_ideal':
        return const Color(0xFFB7791F);
      case 'above_ideal':
        return const Color(0xFFD1495B);
      default:
        return const Color(0xFF5C677D);
    }
  }

  String _statusLabel() {
    switch (metric.status) {
      case 'within_ideal':
        return 'Within ideal';
      case 'below_ideal':
        return 'Below ideal';
      case 'above_ideal':
        return 'Above ideal';
      default:
        return 'Reference unavailable';
    }
  }

  String _valueLabel() {
    final raw = metric.value.toStringAsFixed(metric.value.abs() >= 100 ? 1 : 3);
    return metric.unit.isEmpty ? raw : '$raw ${metric.unit}';
  }

  String? _idealLabel() {
    if (metric.idealMin == null || metric.idealMax == null) {
      return null;
    }
    return 'Ideal: ${metric.idealMin!.toStringAsFixed(1)} to ${metric.idealMax!.toStringAsFixed(1)} ${metric.unit}';
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final statusColor = _statusColor();
    final idealLabel = _idealLabel();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    metric.label,
                    style: theme.textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w700,
                      color: const Color(0xFF14213D),
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    _valueLabel(),
                    style: theme.textTheme.bodyLarge?.copyWith(
                      fontWeight: FontWeight.w700,
                      color: const Color(0xFF1F2937),
                    ),
                  ),
                ],
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: statusColor.withOpacity(0.12),
                borderRadius: BorderRadius.circular(999),
              ),
              child: Text(
                _statusLabel(),
                style: theme.textTheme.labelMedium?.copyWith(
                  color: statusColor,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ],
        ),
        if (idealLabel != null) ...[
          const SizedBox(height: 10),
          Text(
            idealLabel,
            style: theme.textTheme.bodySmall?.copyWith(
              color: const Color(0xFF526071),
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
        if (metric.interpretation.isNotEmpty) ...[
          const SizedBox(height: 8),
          Text(
            metric.interpretation,
            style: theme.textTheme.bodySmall?.copyWith(
              color: const Color(0xFF526071),
              height: 1.4,
            ),
          ),
        ],
        const SizedBox(height: 8),
        Text(
          'Formula: ${metric.formula}',
          style: theme.textTheme.bodySmall?.copyWith(
            color: const Color(0xFF7A8798),
            fontStyle: FontStyle.italic,
          ),
        ),
        for (final note in metric.notes) ...[
          const SizedBox(height: 6),
          Text(
            note,
            style: theme.textTheme.bodySmall?.copyWith(
              color: const Color(0xFF7A8798),
            ),
          ),
        ],
      ],
    );
  }
}
