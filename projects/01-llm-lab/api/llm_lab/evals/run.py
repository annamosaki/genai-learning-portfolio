"""CLI runner for evaluations."""

import asyncio
import json
import yaml
import time
from pathlib import Path
from typing import List, Dict, Any
from ..config import settings
from ..levels import run_level, get_level_info
from ..models import LevelOpts
from .metrics import batch_evaluate


async def load_questions() -> List[Dict[str, Any]]:
    """Load evaluation questions from YAML file."""
    questions_file = Path(__file__).parent / "questions.yaml"
    
    try:
        with open(questions_file, 'r') as f:
            data = yaml.safe_load(f)
            return data.get('questions', [])
    except Exception as e:
        print(f"Error loading questions: {e}")
        return []


async def run_evaluation(
    levels: List[str] = None, 
    questions_subset: int = None,
    output_file: str = None
) -> Dict[str, Any]:
    """
    Run evaluation on specified levels with evaluation questions.
    
    Args:
        levels: List of level IDs to evaluate (default: all)
        questions_subset: Number of questions to use (default: all)
        output_file: Path to save results JSON (default: data/index/eval-report.json)
    """
    # Load questions
    questions = await load_questions()
    if not questions:
        return {"error": "No evaluation questions loaded"}
    
    # Limit questions if specified
    if questions_subset and questions_subset < len(questions):
        questions = questions[:questions_subset]
    
    # Determine levels to evaluate
    if not levels:
        level_info = get_level_info()
        levels = [level.id for level in level_info]
    
    print(f"Running evaluation on {len(levels)} levels with {len(questions)} questions...")
    
    # Run evaluations
    start_time = time.time()
    results = {}
    
    for level_id in levels:
        print(f"Evaluating level: {level_id}")
        level_results = []
        
        for question_data in questions:
            question = question_data["question"]
            
            try:
                # Run the level
                result = await run_level(
                    level_id=level_id,
                    question=question,
                    history=[],
                    opts=LevelOpts()
                )
                
                # Prepare metadata for evaluation
                metadata = {
                    'question_id': question_data['id'],
                    'expected_answer': question_data.get('expected_answer', ''),
                    'category': question_data.get('category', 'unknown'),
                    'difficulty': question_data.get('difficulty', 'unknown'),
                    'expected_keywords': question_data.get('expected_keywords', [])
                }
                
                level_results.append((result, metadata))
                
            except Exception as e:
                print(f"Error evaluating {level_id} on question {question_data['id']}: {e}")
                # Create dummy result for failed cases
                from ..models import LevelResult
                failed_result = LevelResult(
                    answer=f"Evaluation failed: {str(e)}",
                    citations=[],
                    level=level_id,
                    trace={"evaluation_error": str(e)}
                )
                
                metadata = {
                    'question_id': question_data['id'],
                    'expected_answer': '',
                    'category': 'error',
                    'difficulty': 'unknown'
                }
                
                level_results.append((failed_result, metadata))
        
        # Evaluate this level's results
        level_evaluation = batch_evaluate(level_results)
        results[level_id] = level_evaluation
    
    # Compile final report
    total_time = time.time() - start_time
    
    report = {
        'evaluation_metadata': {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'levels_evaluated': levels,
            'questions_count': len(questions),
            'total_runtime_seconds': total_time
        },
        'level_results': results,
        'overall_summary': _compute_overall_summary(results)
    }
    
    # Save report
    if not output_file:
        output_file = Path(settings.index_dir) / "eval-report.json"
    
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"Evaluation complete! Report saved to: {output_path}")
    return report


def _compute_overall_summary(results: Dict[str, Any]) -> Dict[str, Any]:
    """Compute cross-level summary statistics."""
    if not results:
        return {}
    
    level_scores = {}
    all_scores = []
    
    for level_id, level_data in results.items():
        if 'summary' in level_data:
            level_score = level_data['summary']['avg_overall_score']
            level_scores[level_id] = level_score
            all_scores.append(level_score)
    
    if not all_scores:
        return {"error": "No valid scores to summarize"}
    
    # Rank levels by performance
    ranked_levels = sorted(level_scores.items(), key=lambda x: x[1], reverse=True)
    
    return {
        'best_performing_level': ranked_levels[0][0] if ranked_levels else None,
        'worst_performing_level': ranked_levels[-1][0] if ranked_levels else None,
        'average_score_across_levels': sum(all_scores) / len(all_scores),
        'performance_ranking': [{'level': level, 'score': score} for level, score in ranked_levels],
        'score_range': {
            'highest': max(all_scores),
            'lowest': min(all_scores),
            'spread': max(all_scores) - min(all_scores)
        }
    }


if __name__ == "__main__":
    import sys
    
    # Simple CLI interface
    levels = None
    questions_count = None
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help":
            print("Usage: python -m llm_lab.evals.run [level1,level2,...] [question_count]")
            print("Examples:")
            print("  python -m llm_lab.evals.run                    # All levels, all questions")
            print("  python -m llm_lab.evals.run naive_rag,smart_rag  # Specific levels")  
            print("  python -m llm_lab.evals.run all 5              # All levels, 5 questions")
            sys.exit(0)
        
        if sys.argv[1] != "all":
            levels = [l.strip() for l in sys.argv[1].split(',')]
    
    if len(sys.argv) > 2:
        try:
            questions_count = int(sys.argv[2])
        except ValueError:
            print("Invalid question count, using all questions")
    
    asyncio.run(run_evaluation(levels, questions_count))