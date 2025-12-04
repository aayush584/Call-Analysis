"""
Question Evaluator using LLM to analyze call transcripts
"""

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from typing import List, Optional
import json
from questions_config import PREDEFINED_QUESTIONS, QUESTION_CATEGORIES


class QuestionEvaluation(BaseModel):
    """Schema for individual question evaluation"""
    question_id: str = Field(description="The question ID")
    status: str = Field(description="Status: YES, NO, PARTIAL, or N/A")
    confidence: int = Field(description="Confidence score 1-100")
    evidence: str = Field(description="Brief evidence from transcript supporting the answer")
    reasoning: str = Field(description="Explanation for the evaluation")


class CallEvaluator:
    def __init__(self, model_name: str = "gpt-oss:20b-cloud"):
        self.llm = ChatOllama(
            model=model_name,
            temperature=0.1
        )
        self.questions = PREDEFINED_QUESTIONS
        self.categories = QUESTION_CATEGORIES
        
    def evaluate_questions(self, transcript: str, summary: str, 
                          questions: List[dict] = None) -> dict:
        """
        Evaluate all questions against the transcript and summary.
        
        Args:
            transcript: The full transcript text
            summary: The call summary
            questions: Optional custom questions, uses predefined if None
            
        Returns:
            Dictionary containing evaluations and scores
        """
        if questions is None:
            questions = self.questions
            
        evaluations = []
        
        # Process questions in batches for efficiency
        batch_size = 5
        for i in range(0, len(questions), batch_size):
            batch = questions[i:i + batch_size]
            batch_results = self._evaluate_batch(transcript, summary, batch)
            evaluations.extend(batch_results)
            
        # Calculate scores
        scores = self._calculate_scores(evaluations)
        
        # Group by category
        categorized = self._group_by_category(evaluations)
        
        return {
            "evaluations": evaluations,
            "scores": scores,
            "by_category": categorized,
            "total_questions": len(questions)
        }
    
    def _evaluate_batch(self, transcript: str, summary: str, 
                        questions: List[dict]) -> List[dict]:
        """Evaluate a batch of questions"""
        
        questions_text = "\n".join([
            f"{i+1}. [{q['id']}] {q['question']}\n   Context: {q['description']}"
            for i, q in enumerate(questions)
        ])
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert call quality analyst. Analyze the call transcript and summary to evaluate each question.

For each question, provide:
- status: "YES" (clearly met), "NO" (clearly not met), "PARTIAL" (partially met), or "N/A" (not applicable/cannot determine)
- confidence: 1-100 score indicating how confident you are
- evidence: A brief quote or reference from the transcript that supports your answer
- reasoning: A short explanation of your evaluation

Be objective and base your evaluation strictly on the transcript content.

Respond in valid JSON format as an array of evaluations."""),
            ("human", """## Call Summary:
{summary}

## Full Transcript:
{transcript}

## Questions to Evaluate:
{questions}

Evaluate each question and respond with a JSON array:
[
  {{
    "question_id": "id",
    "status": "YES/NO/PARTIAL/N/A",
    "confidence": 85,
    "evidence": "relevant quote from transcript",
    "reasoning": "explanation"
  }},
  ...
]""")
        ])
        
        try:
            chain = prompt | self.llm
            response = chain.invoke({
                "summary": summary,
                "transcript": transcript,
                "questions": questions_text
            })
            
            # Parse JSON response
            response_text = response.content
            
            # Extract JSON from response
            json_start = response_text.find('[')
            json_end = response_text.rfind(']') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                results = json.loads(json_str)
                
                # Add category info to each result
                for result in results:
                    q = next((q for q in questions if q['id'] == result['question_id']), None)
                    if q:
                        result['category'] = q.get('category', 'General')
                        result['question'] = q['question']
                        result['weight'] = q.get('weight', 1)
                        
                return results
            else:
                # Fallback if JSON parsing fails
                return self._create_fallback_results(questions)
                
        except Exception as e:
            print(f"Error evaluating batch: {e}")
            return self._create_fallback_results(questions)
    
    def _create_fallback_results(self, questions: List[dict]) -> List[dict]:
        """Create fallback results if evaluation fails"""
        return [
            {
                "question_id": q['id'],
                "question": q['question'],
                "category": q.get('category', 'General'),
                "status": "N/A",
                "confidence": 0,
                "evidence": "Evaluation failed",
                "reasoning": "Could not evaluate due to an error",
                "weight": q.get('weight', 1)
            }
            for q in questions
        ]
    
    def _calculate_scores(self, evaluations: List[dict]) -> dict:
        """Calculate various scores from evaluations"""
        
        total_weight = sum(e.get('weight', 1) for e in evaluations)
        
        # Calculate weighted scores
        status_scores = {"YES": 1.0, "PARTIAL": 0.5, "NO": 0, "N/A": None}
        
        weighted_sum = 0
        applicable_weight = 0
        
        status_counts = {"YES": 0, "NO": 0, "PARTIAL": 0, "N/A": 0}
        
        for e in evaluations:
            status = e.get('status', 'N/A').upper()
            weight = e.get('weight', 1)
            status_counts[status] = status_counts.get(status, 0) + 1
            
            score = status_scores.get(status)
            if score is not None:
                weighted_sum += score * weight
                applicable_weight += weight
        
        overall_score = round((weighted_sum / applicable_weight * 100), 1) if applicable_weight > 0 else 0
        
        # Average confidence
        confidences = [e.get('confidence', 0) for e in evaluations if e.get('status') != 'N/A']
        avg_confidence = round(sum(confidences) / len(confidences), 1) if confidences else 0
        
        return {
            "overall_score": overall_score,
            "average_confidence": avg_confidence,
            "status_counts": status_counts,
            "applicable_questions": len([e for e in evaluations if e.get('status') != 'N/A']),
            "grade": self._get_grade(overall_score)
        }
    
    def _get_grade(self, score: float) -> str:
        """Convert score to letter grade"""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
    
    def _group_by_category(self, evaluations: List[dict]) -> dict:
        """Group evaluations by category with category scores"""
        
        categories = {}
        
        for e in evaluations:
            cat = e.get('category', 'General')
            if cat not in categories:
                categories[cat] = {
                    "questions": [],
                    "info": self.categories.get(cat, {
                        "description": cat,
                        "icon": "fa-question",
                        "color": "#64748b"
                    })
                }
            categories[cat]["questions"].append(e)
        
        # Calculate category scores
        status_scores = {"YES": 1.0, "PARTIAL": 0.5, "NO": 0, "N/A": None}
        
        for cat, data in categories.items():
            questions = data["questions"]
            applicable = [q for q in questions if q.get('status') != 'N/A']
            
            if applicable:
                total = sum(status_scores.get(q.get('status', 'N/A').upper(), 0) for q in applicable)
                data["score"] = round(total / len(applicable) * 100, 1)
            else:
                data["score"] = None
                
            data["total"] = len(questions)
            data["passed"] = len([q for q in questions if q.get('status') == 'YES'])
            
        return categories


def evaluate_call(transcript: str, summary: str, 
                  custom_questions: List[dict] = None) -> dict:
    """
    Convenience function to evaluate a call.
    
    Args:
        transcript: Full transcript text
        summary: Call summary
        custom_questions: Optional custom questions
        
    Returns:
        Evaluation results
    """
    evaluator = CallEvaluator()
    return evaluator.evaluate_questions(transcript, summary, custom_questions)