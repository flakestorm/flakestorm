//! flakestorm Rust Performance Module
//!
//! This module provides high-performance implementations for:
//! - Robustness score calculation
//! - Parallel mutation processing
//! - Fast string similarity scoring

use pyo3::prelude::*;
use rayon::prelude::*;

mod parallel;
mod scoring;

pub use parallel::*;
pub use scoring::*;

/// Calculate the robustness score for a test run.
///
/// The robustness score R is calculated as:
/// R = (W_s * S_passed + W_d * D_passed) / N_total
///
/// Where:
/// - S_passed = Semantic variations passed
/// - D_passed = Deterministic tests passed
/// - W_s, W_d = Weights for semantic and deterministic tests
#[pyfunction]
fn calculate_robustness_score(
    semantic_passed: u32,
    deterministic_passed: u32,
    total: u32,
    semantic_weight: f64,
    deterministic_weight: f64,
) -> f64 {
    if total == 0 {
        return 0.0;
    }

    let weighted_sum = semantic_weight * semantic_passed as f64
        + deterministic_weight * deterministic_passed as f64;

    weighted_sum / total as f64
}

/// Calculate weighted robustness score with per-mutation weights.
///
/// Each mutation has its own weight based on difficulty.
/// Passing a prompt injection attack is worth more than passing a typo test.
#[pyfunction]
fn calculate_weighted_score(
    results: Vec<(bool, f64)>,  // (passed, weight)
) -> f64 {
    if results.is_empty() {
        return 0.0;
    }

    let total_weight: f64 = results.iter().map(|(_, w)| w).sum();
    let passed_weight: f64 = results
        .iter()
        .filter(|(passed, _)| *passed)
        .map(|(_, w)| w)
        .sum();

    if total_weight == 0.0 {
        return 0.0;
    }

    passed_weight / total_weight
}

/// Process mutations in parallel and return results.
///
/// Uses Rayon for efficient parallel processing.
#[pyfunction]
fn parallel_process_mutations(
    mutations: Vec<String>,
    mutation_types: Vec<String>,
    weights: Vec<f64>,
) -> Vec<(String, String, f64)> {
    mutations
        .into_par_iter()
        .enumerate()
        .map(|(i, mutation)| {
            let mutation_type = mutation_types.get(i % mutation_types.len())
                .cloned()
                .unwrap_or_else(|| "unknown".to_string());
            let weight = weights.get(i % weights.len())
                .copied()
                .unwrap_or(1.0);
            (mutation, mutation_type, weight)
        })
        .collect()
}

/// Fast Levenshtein distance calculation for noise mutation validation.
#[pyfunction]
fn levenshtein_distance(s1: &str, s2: &str) -> usize {
    let len1 = s1.chars().count();
    let len2 = s2.chars().count();

    if len1 == 0 {
        return len2;
    }
    if len2 == 0 {
        return len1;
    }

    let s1_chars: Vec<char> = s1.chars().collect();
    let s2_chars: Vec<char> = s2.chars().collect();

    let mut prev_row: Vec<usize> = (0..=len2).collect();
    let mut curr_row: Vec<usize> = vec![0; len2 + 1];

    for i in 1..=len1 {
        curr_row[0] = i;
        for j in 1..=len2 {
            let cost = if s1_chars[i - 1] == s2_chars[j - 1] { 0 } else { 1 };
            curr_row[j] = std::cmp::min(
                std::cmp::min(prev_row[j] + 1, curr_row[j - 1] + 1),
                prev_row[j - 1] + cost,
            );
        }
        std::mem::swap(&mut prev_row, &mut curr_row);
    }

    prev_row[len2]
}

/// Calculate similarity ratio between two strings (0.0 to 1.0).
#[pyfunction]
fn string_similarity(s1: &str, s2: &str) -> f64 {
    let distance = levenshtein_distance(s1, s2);
    let max_len = std::cmp::max(s1.chars().count(), s2.chars().count());

    if max_len == 0 {
        return 1.0;
    }

    1.0 - (distance as f64 / max_len as f64)
}

/// V2: Contract resilience matrix score (addendum §6.3).
///
/// severity_weight: critical=3, high=2, medium=1, low=1.
/// Returns (score_0_100, overall_passed, critical_failed).
#[pyfunction]
fn calculate_resilience_matrix_score(
    severities: Vec<String>,
    passed: Vec<bool>,
) -> (f64, bool, bool) {
    let n = std::cmp::min(severities.len(), passed.len());
    if n == 0 {
        return (100.0, true, false);
    }

    const SEVERITY_WEIGHT: &[(&str, f64)] = &[
        ("critical", 3.0),
        ("high", 2.0),
        ("medium", 1.0),
        ("low", 1.0),
    ];

    let weight_for = |s: &str| -> f64 {
        let lower = s.to_lowercase();
        SEVERITY_WEIGHT
            .iter()
            .find(|(k, _)| *k == lower)
            .map(|(_, w)| *w)
            .unwrap_or(1.0)
    };

    let mut weighted_pass = 0.0;
    let mut weighted_total = 0.0;
    let mut critical_failed = false;

    for i in 0..n {
        let w = weight_for(severities[i].as_str());
        weighted_total += w;
        if passed[i] {
            weighted_pass += w;
        } else if severities[i].eq_ignore_ascii_case("critical") {
            critical_failed = true;
        }
    }

    let score = if weighted_total == 0.0 {
        100.0
    } else {
        (weighted_pass / weighted_total) * 100.0
    };
    let score = (score * 100.0).round() / 100.0;
    let overall_passed = !critical_failed;

    (score, overall_passed, critical_failed)
}

/// V2: Overall resilience score from component scores and weights.
///
/// Weighted average: sum(scores[i] * weights[i]) / sum(weights[i]).
/// Used for mutation_robustness, chaos_resilience, contract_compliance, replay_regression.
#[pyfunction]
fn calculate_overall_resilience(scores: Vec<f64>, weights: Vec<f64>) -> f64 {
    let n = std::cmp::min(scores.len(), weights.len());
    if n == 0 {
        return 1.0;
    }
    let mut sum_w = 0.0;
    let mut sum_ws = 0.0;
    for i in 0..n {
        sum_w += weights[i];
        sum_ws += scores[i] * weights[i];
    }
    if sum_w == 0.0 {
        return 1.0;
    }
    sum_ws / sum_w
}

/// Python module definition
#[pymodule]
fn flakestorm_rust(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(calculate_robustness_score, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_weighted_score, m)?)?;
    m.add_function(wrap_pyfunction!(parallel_process_mutations, m)?)?;
    m.add_function(wrap_pyfunction!(levenshtein_distance, m)?)?;
    m.add_function(wrap_pyfunction!(string_similarity, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_resilience_matrix_score, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_overall_resilience, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_robustness_score() {
        let score = calculate_robustness_score(8, 10, 20, 1.0, 1.0);
        assert!((score - 0.9).abs() < 0.001);
    }

    #[test]
    fn test_weighted_score() {
        let results = vec![
            (true, 1.0),
            (true, 1.5),
            (false, 1.0),
        ];
        let score = calculate_weighted_score(results);
        assert!((score - 0.714).abs() < 0.01);
    }

    #[test]
    fn test_levenshtein() {
        assert_eq!(levenshtein_distance("kitten", "sitting"), 3);
        assert_eq!(levenshtein_distance("", "abc"), 3);
        assert_eq!(levenshtein_distance("abc", "abc"), 0);
    }

    #[test]
    fn test_string_similarity() {
        let sim = string_similarity("hello", "hallo");
        assert!(sim > 0.7 && sim < 0.9);
    }

    #[test]
    fn test_resilience_matrix_score() {
        let (score, overall, critical) = calculate_resilience_matrix_score(
            vec!["critical".into(), "high".into(), "medium".into()],
            vec![true, true, false],
        );
        assert!((score - (3.0 + 2.0) / (3.0 + 2.0 + 1.0) * 100.0).abs() < 0.01);
        assert!(overall);
        assert!(!critical);

        let (_, _, critical_fail) = calculate_resilience_matrix_score(
            vec!["critical".into()],
            vec![false],
        );
        assert!(critical_fail);
    }

    #[test]
    fn test_overall_resilience() {
        let s = calculate_overall_resilience(vec![0.8, 1.0, 0.5], vec![0.25, 0.25, 0.5]);
        assert!((s - (0.8 * 0.25 + 1.0 * 0.25 + 0.5 * 0.5) / 1.0).abs() < 0.001);
        assert_eq!(calculate_overall_resilience(vec![], vec![]), 1.0);
    }
}
