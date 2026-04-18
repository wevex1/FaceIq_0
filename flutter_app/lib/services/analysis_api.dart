import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../models/analysis_result.dart';

class AnalysisApi {
  AnalysisApi({required this.baseUrl});

  final String baseUrl;

  Future<AnalysisResult> analyze({
    required String frontImagePath,
    required String sideImagePath,
  }) async {
    final uri = Uri.parse('$baseUrl/analyze');
    final request = http.MultipartRequest('POST', uri)
      ..files.add(await http.MultipartFile.fromPath('front_image', frontImagePath))
      ..files.add(await http.MultipartFile.fromPath('side_image', sideImagePath));

    http.StreamedResponse streamedResponse;
    try {
      streamedResponse = await request.send();
    } on SocketException {
      throw AnalysisApiException(
        'Could not reach the Python backend. Start the FastAPI server on $baseUrl before running analysis.',
      );
    }

    final response = await http.Response.fromStream(streamedResponse);
    final payload = response.body.isEmpty
        ? <String, dynamic>{}
        : jsonDecode(response.body) as Map<String, dynamic>;

    if (response.statusCode >= 400) {
      final detail = payload['detail'];
      throw AnalysisApiException(detail?.toString() ?? 'Analysis failed with HTTP ${response.statusCode}.');
    }

    return AnalysisResult.fromJson(payload);
  }
}

class AnalysisApiException implements Exception {
  AnalysisApiException(this.message);

  final String message;

  @override
  String toString() => message;
}
