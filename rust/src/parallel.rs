//! Parallel processing utilities for Entropix
//!
//! This module provides efficient parallel processing for mutation generation
//! and agent testing using Rayon.

use rayon::prelude::*;

/// Process items in parallel with a maximum concurrency limit.
pub fn parallel_map<T, U, F>(items: Vec<T>, max_concurrency: usize, f: F) -> Vec<U>
where
    T: Send + Sync,
    U: Send,
    F: Fn(T) -> U + Send + Sync,
{
    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(max_concurrency)
        .build()
        .unwrap_or_else(|_| rayon::ThreadPoolBuilder::new().build().unwrap());
    
    pool.install(|| {
        items.into_par_iter().map(f).collect()
    })
}

/// Batch processing with progress callback.
pub fn parallel_batch_process<T, U, F, P>(
    items: Vec<T>,
    batch_size: usize,
    f: F,
    _progress_callback: P,
) -> Vec<U>
where
    T: Send + Sync + Clone,
    U: Send,
    F: Fn(&[T]) -> Vec<U> + Send + Sync,
    P: Fn(usize, usize) + Send + Sync,
{
    let batches: Vec<Vec<T>> = items
        .chunks(batch_size)
        .map(|chunk| chunk.to_vec())
        .collect();
    
    batches
        .into_par_iter()
        .flat_map(|batch| f(&batch))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parallel_map() {
        let items = vec![1, 2, 3, 4, 5];
        let results = parallel_map(items, 2, |x| x * 2);
        assert_eq!(results, vec![2, 4, 6, 8, 10]);
    }
}

