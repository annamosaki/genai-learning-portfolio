"""Simple evaluation metrics for assessing LLM responses."""

import re
from typing import List, Dict, Any, Tuple
from ..models import LevelResult


def calculate_faithfulness_score(answer: str, citations: List[str], context: str = "") -> float:
    """
    Simple faithfulness heuristic - check if answer makes claims supported by citations.
    
    This is a simplified version - real faithfulness would require more sophisticated NLU.
    """
    if not citations:
        # No citations provided - assume low faithfulness for factual claims
        factual_indicators = ["is", "was", "are", "were", "has", "have", "will", "reported", "according to"]
        factual_count = sum(1 for indicator in factual_indicators if indicator in answer.lower())
        
        if factual_count > 3:
            return 0.3  # Likely making unsupported claims
        else:
            return 0.7  # Seems more like general analysis
    
    # Has citations - higher baseline faithfulness
    citation_count = len(citations)
    
    # Check for proper citation format [1], [2] etc in answer
    citation_pattern = r'\[\d+\]'
    inline_citations = len(re.findall(citation_pattern, answer))
    
    # Score based on citation usage
    if inline_citations > 0:
        return min(0.9, 0.7 + (inline_citations * 0.1))
    else:
        return 0.6  # Has sources but doesn't cite them inline


def calculate_citation_precision(answer: str, citations: List[str]) -> float:
    """
    Check if cited sources are actually relevant to the claims made.
    
    Simplified heuristic based on citation patterns and answer content.
    """
    if not citations:
        return 0.0
    
    # Check for inline citation usage
    citation_pattern = r'\[\d+\]'
    inline_citations = re.findall(citation_pattern, answer)
    
    if not inline_citations:
        return 0.5  # Has sources but doesn't use them properly
    
    # Higher score if multiple citations used appropriately
    unique_citations = set(inline_citations)
    citation_variety = len(unique_citations) / max(len(citations), 1)
    
    return min(1.0, 0.6 + (citation_variety * 0.4))


def calculate_completeness_score(answer: str, expected_keywords: List[str] = None) -> float:
    """
    Assess how complete the answer is based on length and keyword coverage.
    """
    # Length-based scoring
    word_count = len(answer.split())
    
    if word_count < 20:
        length_score = 0.3
    elif word_count < 50:
        length_score = 0.6
    elif word_count < 100:
        length_score = 0.8
    else:
        length_score = 1.0
    
    # Keyword coverage (if provided)
    if expected_keywords:
        answer_lower = answer.lower()
        keyword_hits = sum(1 for keyword in expected_keywords if keyword.lower() in answer_lower)
        keyword_score = keyword_hits / len(expected_keywords)
    else:
        keyword_score = 0.7  # Default when no keywords provided
    
    return (length_score * 0.6) + (keyword_score * 0.4)


def calculate_clarity_score(answer: str) -> float:
    """
    Assess clarity based on sentence structure and readability heuristics.
    """
    sentences = re.split(r'[.!?]+', answer)
    sentence_count = len([s for s in sentences if s.strip()])
    
    if sentence_count == 0:
        return 0.0
    
    avg_sentence_length = len(answer.split()) / sentence_count
    
    # Optimal sentence length is around 15-20 words
    if 10 <= avg_sentence_length <= 25:
        length_score = 1.0
    elif 5 <= avg_sentence_length <= 35:
        length_score = 0.7
    else:
        length_score = 0.4
    
    # Check for good structure indicators
    structure_indicators = [
        answer.count(',') > 0,  # Uses commas
        answer.count(';') > 0,  # Uses semicolons
        any(word in answer.lower() for word in ['however', 'therefore', 'additionally', 'furthermore']),  # Connectors
        sentence_count > 1,  # Multiple sentences
    ]
    
    structure_score = sum(structure_indicators) / len(structure_indicators)
    
    return (length_score * 0.7) + (structure_score * 0.3)


def evaluate_response(
    result: LevelResult,
    expected_answer: str = "",
    expected_keywords: List[str] = None,
    context: str = ""
) -> Dict[str, Any]:
    """
    Comprehensive evaluation of a LevelResult.
    
    Returns:
        Dictionary with individual scores and overall assessment
    """
    answer = result.answer
    citations = result.citations
    
    # Calculate individual metrics
    faithfulness = calculate_faithfulness_score(answer, citations, context)
    citation_precision = calculate_citation_precision(answer, citations)
    completeness = calculate_completeness_score(answer, expected_keywords)
    clarity = calculate_clarity_score(answer)
    
    # Overall score (weighted average)
    weights = {
        'faithfulness': 0.3,
        'citation_precision': 0.25,
        'completeness': 0.25,
        'clarity': 0.2
    }
    
    overall_score = (
        faithfulness * weights['faithfulness'] +
        citation_precision * weights['citation_precision'] +
        completeness * weights['completeness'] +
        clarity * weights['clarity']
    )
    
    return {
        'overall_score': overall_score,
        'metrics': {
            'faithfulness': faithfulness,
            'citation_precision': citation_precision,
            'completeness': completeness,
            'clarity': clarity
        },
        'details': {
            'answer_length': len(answer.split()),
            'citation_count': len(citations),
            'inline_citations': len(re.findall(r'\[\d+\]', answer)),
            'sentence_count': len(re.split(r'[.!?]+', answer)),
            'level': result.level
        }
    }


def batch_evaluate(results: List[Tuple[LevelResult, Dict[str, Any]]]) -> Dict[str, Any]:
    """
    Evaluate multiple results and provide aggregate statistics.
    
    Args:
        results: List of (LevelResult, evaluation_metadata) tuples
        
    Returns:
        Aggregate evaluation statistics
    """
    if not results:
        return {"error": "No results to evaluate"}
    
    evaluations = []
    
    for result, metadata in results:
        expected_keywords = metadata.get('expected_keywords', [])
        expected_answer = metadata.get('expected_answer', '')
        
        eval_result = evaluate_response(result, expected_answer, expected_keywords)
        eval_result['question_id'] = metadata.get('question_id', 'unknown')
        eval_result['category'] = metadata.get('category', 'unknown')
        evaluations.append(eval_result)
    
    # Aggregate statistics
    overall_scores = [e['overall_score'] for e in evaluations]
    faithfulness_scores = [e['metrics']['faithfulness'] for e in evaluations]
    citation_scores = [e['metrics']['citation_precision'] for e in evaluations]
    
    return {
        'summary': {
            'total_questions': len(evaluations),
            'avg_overall_score': sum(overall_scores) / len(overall_scores),
            'avg_faithfulness': sum(faithfulness_scores) / len(faithfulness_scores),
            'avg_citation_precision': sum(citation_scores) / len(citation_scores),
            'score_distribution': {
                'excellent': len([s for s in overall_scores if s >= 0.8]),
                'good': len([s for s in overall_scores if 0.6 <= s < 0.8]),
                'fair': len([s for s in overall_scores if 0.4 <= s < 0.6]),
                'poor': len([s for s in overall_scores if s < 0.4])
            }
        },
        'detailed_results': evaluations
    }