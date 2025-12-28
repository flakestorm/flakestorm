//! Scoring algorithms for Entropix
//!
//! This module contains optimized scoring algorithms for calculating
//! robustness metrics and aggregating test results.

use serde::{Deserialize, Serialize};

/// Result of a single mutation test
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MutationResult {
    pub mutation_type: String,
    pub passed: bool,
    pub weight: f64,
    pub latency_ms: f64,
    pub checks: Vec<CheckResult>,
}

/// Result of a single invariant check
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CheckResult {
    pub check_type: String,
    pub passed: bool,
    pub details: String,
}

/// Aggregate statistics for a test run
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TestStatistics {
    pub total_mutations: usize,
    pub passed_mutations: usize,
    pub failed_mutations: usize,
    pub robustness_score: f64,
    pub avg_latency_ms: f64,
    pub p50_latency_ms: f64,
    pub p95_latency_ms: f64,
    pub p99_latency_ms: f64,
    pub by_type: Vec<TypeStatistics>,
}

/// Statistics broken down by mutation type
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TypeStatistics {
    pub mutation_type: String,
    pub total: usize,
    pub passed: usize,
    pub pass_rate: f64,
}

/// Calculate comprehensive statistics from mutation results
pub fn calculate_statistics(results: &[MutationResult]) -> TestStatistics {
    let total = results.len();
    let passed = results.iter().filter(|r| r.passed).count();
    let failed = total - passed;
    
    // Calculate robustness score
    let total_weight: f64 = results.iter().map(|r| r.weight).sum();
    let passed_weight: f64 = results
        .iter()
        .filter(|r| r.passed)
        .map(|r| r.weight)
        .sum();
    
    let robustness_score = if total_weight > 0.0 {
        passed_weight / total_weight
    } else {
        0.0
    };
    
    // Calculate latency statistics
    let mut latencies: Vec<f64> = results.iter().map(|r| r.latency_ms).collect();
    latencies.sort_by(|a, b| a.partial_cmp(b).unwrap());
    
    let avg_latency = if !latencies.is_empty() {
        latencies.iter().sum::<f64>() / latencies.len() as f64
    } else {
        0.0
    };
    
    let p50 = percentile(&latencies, 50);
    let p95 = percentile(&latencies, 95);
    let p99 = percentile(&latencies, 99);
    
    // Statistics by mutation type
    let mut type_stats = std::collections::HashMap::new();
    for result in results {
        let entry = type_stats
            .entry(result.mutation_type.clone())
            .or_insert((0usize, 0usize));
        entry.0 += 1;
        if result.passed {
            entry.1 += 1;
        }
    }
    
    let by_type: Vec<TypeStatistics> = type_stats
        .into_iter()
        .map(|(mutation_type, (total, passed))| TypeStatistics {
            mutation_type,
            total,
            passed,
            pass_rate: passed as f64 / total as f64,
        })
        .collect();
    
    TestStatistics {
        total_mutations: total,
        passed_mutations: passed,
        failed_mutations: failed,
        robustness_score,
        avg_latency_ms: avg_latency,
        p50_latency_ms: p50,
        p95_latency_ms: p95,
        p99_latency_ms: p99,
        by_type,
    }
}

/// Calculate percentile from sorted values
fn percentile(sorted_values: &[f64], p: usize) -> f64 {
    if sorted_values.is_empty() {
        return 0.0;
    }
    
    let index = (p as f64 / 100.0 * (sorted_values.len() - 1) as f64).round() as usize;
    sorted_values[index.min(sorted_values.len() - 1)]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_percentile() {
        let values = vec![1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0];
        assert!((percentile(&values, 50) - 5.5).abs() < 1.0);
        assert!((percentile(&values, 95) - 9.5).abs() < 1.0);
    }

    #[test]
    fn test_calculate_statistics() {
        let results = vec![
            MutationResult {
                mutation_type: "paraphrase".to_string(),
                passed: true,
                weight: 1.0,
                latency_ms: 100.0,
                checks: vec![],
            },
            MutationResult {
                mutation_type: "noise".to_string(),
                passed: true,
                weight: 0.8,
                latency_ms: 150.0,
                checks: vec![],
            },
            MutationResult {
                mutation_type: "prompt_injection".to_string(),
                passed: false,
                weight: 1.5,
                latency_ms: 200.0,
                checks: vec![],
            },
        ];
        
        let stats = calculate_statistics(&results);
        assert_eq!(stats.total_mutations, 3);
        assert_eq!(stats.passed_mutations, 2);
        assert_eq!(stats.failed_mutations, 1);
        assert!(stats.robustness_score > 0.5);
    }
}

