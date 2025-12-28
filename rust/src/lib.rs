//! Entropix Rust Performance Module
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

/// Python module definition
#[pymodule]
fn entropix_rust(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(calculate_robustness_score, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_weighted_score, m)?)?;
    m.add_function(wrap_pyfunction!(parallel_process_mutations, m)?)?;
    m.add_function(wrap_pyfunction!(levenshtein_distance, m)?)?;
    m.add_function(wrap_pyfunction!(string_similarity, m)?)?;
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
}

