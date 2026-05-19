'use client';

import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
import { getSubmissionReviewDetails, submitTrainerReview } from '@/lib/api';
import type { TestSubmission } from '@/lib/api/types';
import { CheckCircle2, Star, Play, Pause, RotateCcw, Loader2, Copy, Lightbulb } from 'lucide-react';
import { useAudioPlayer } from '@/lib/hooks/useAudioPlayer';
import { formatTableDate } from '@/lib/utils/date';

interface SubmissionReviewSheetProps {
  submission: TestSubmission | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onReviewSuccess?: () => void;
  readOnly?: boolean; // If true, show existing review in read-only mode (for GRADED submissions)
}

interface ReviewDetails {
  submission: TestSubmission;
  test: {
    id: number;
    name: string;
    test_type: string;
    role?: string;
    curriculum?: string;
    duration_seconds?: number;
    skills: Array<{ id: number; name: string; description?: string }>;
  };
  transcript: {
    session_id: string;
    submission_id: number;
    test_name: string;
    test_role?: string;
    messages: Array<{
      role: string;
      content: string;
      timestamp: string;
    }>;
    audio_urls?: Array<{
      message_index: number;
      audio_url: string;
      uploaded_at: string;
    }>;
    message_count: number;
    duration_seconds?: number;
    status: string;
    created_at: string;
    ended_at?: string;
    lambda_evaluation?: {
      overall_score: number;
      score_breakdown: {
        technical_knowledge?: number;
        problem_solving?: number;
        communication?: number;
        code_quality?: number;
        engagement?: number;
      };
      skill_breakdown: Record<
        string,
        {
          score: number;
          feedback: string;
          proficiency_level: string;
        }
      >;
      feedback: string;
      strengths: string[];
      improvements: string[];
      key_highlights: string[];
      red_flags: string[];
      recommendation: string;
      reasoning: string;
      evaluated_at?: string;
      evaluated_by?: string;
    };
    trainer_evaluation?: {
      overall_score: number;
      score_breakdown?: {
        technical_knowledge?: number;
        problem_solving?: number;
        communication?: number;
        code_quality?: number;
        engagement?: number;
      };
      skill_breakdown?: Record<
        string,
        {
          score: number;
          feedback: string;
          proficiency_level: string;
        }
      >;
      feedback?: string;
      strengths?: string[];
      improvements?: string[];
    };
  };
}

export function SubmissionReviewSheet({
  submission,
  open,
  onOpenChange,
  onReviewSuccess,
  readOnly = false,
}: SubmissionReviewSheetProps) {
  const [details, setDetails] = useState<ReviewDetails | null>(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state - comprehensive trainer evaluation
  const [trainerScore, setTrainerScore] = useState<string>('');
  const [overallFeedback, setOverallFeedback] = useState<string>('');
  const [strengths, setStrengths] = useState<string>('');
  const [improvements, setImprovements] = useState<string>('');

  // Performance breakdown state (editable)
  const [technicalKnowledge, setTechnicalKnowledge] = useState<string>('');
  const [problemSolving, setProblemSolving] = useState<string>('');
  const [communication, setCommunication] = useState<string>('');
  const [codeQuality, setCodeQuality] = useState<string>('');
  const [engagement, setEngagement] = useState<string>('');

  // Skills assessment state
  const [skillsAssessment, setSkillsAssessment] = useState<Record<string, { score: string; feedback: string; proficiency: string }>>({});

  // Audio playback state
  const [playingAudioIndex, setPlayingAudioIndex] = useState<number | null>(null);
  const audioPlayer = useAudioPlayer();

  useEffect(() => {
    if (!submission || !open) {
      setDetails(null);
      setError(null);
      // Reset all form fields
      setTrainerScore('');
      setOverallFeedback('');
      setStrengths('');
      setImprovements('');
      setTechnicalKnowledge('');
      setProblemSolving('');
      setCommunication('');
      setCodeQuality('');
      setEngagement('');
      setSkillsAssessment({});
      return;
    }

    const loadDetails = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await getSubmissionReviewDetails(submission.id);
        setDetails(data);

        // In read-only mode, pre-fill with existing trainer evaluation
        if (readOnly && submission.trainer_score) {
          setTrainerScore(submission.trainer_score.toString());
          if (submission.feedback) {
            setOverallFeedback(submission.feedback);
          }
          // Note: Full trainer_evaluation structure would need to be fetched from MongoDB
          // For now, we show basic fields from submission
        }
      } catch (err) {
        console.error('Failed to load review details:', err);
        setError(err instanceof Error ? err.message : 'Failed to load details');
      } finally {
        setLoading(false);
      }
    };

    loadDetails();
  }, [submission, open]);

  const handlePlayAudio = async (audioUrl: string, messageIndex: number) => {
    // If already playing this audio, pause it
    if (playingAudioIndex === messageIndex && audioPlayer.isPlaying) {
      audioPlayer.pause();
      return;
    }

    // If paused on this audio, resume it
    if (playingAudioIndex === messageIndex && audioPlayer.isPaused) {
      audioPlayer.resume();
      return;
    }

    // Otherwise, play new audio
    setPlayingAudioIndex(messageIndex);
    audioPlayer.onPlaybackEnd(() => {
      setPlayingAudioIndex(null);
    });
    await audioPlayer.play(audioUrl);
  };

  const handlePauseAudio = () => {
    audioPlayer.pause();
  };

  const handleRestartAudio = () => {
    audioPlayer.restart();
  };

  // Helper function to get audio URL for a message by index
  const getAudioUrlForMessage = (messageIndex: number): string | undefined => {
    if (!details?.transcript?.audio_urls) return undefined;
    const audioEntry = details.transcript.audio_urls.find(
      (entry) => entry.message_index === messageIndex
    );
    return audioEntry?.audio_url;
  };

  useEffect(() => {
    return () => {
      audioPlayer.stop();
      setPlayingAudioIndex(null);
    };
  }, [open]);

  const handleUseAIValue = (setter: (value: string) => void, value: string | string[] | undefined) => {
    if (Array.isArray(value)) {
      setter(value.join('\n'));
    } else {
      setter(value || '');
    }
  };

  const handleSubmit = async () => {
    if (!submission || !trainerScore) return;

    const score = parseInt(trainerScore, 10);
    if (isNaN(score) || score < 0 || score > 100) {
      setError('Score must be between 0 and 100');
      return;
    }

    try {
      setSubmitting(true);
      setError(null);

      // Build comprehensive trainer evaluation
      const trainerEvaluation = {
        overall_score: score,
        feedback: overallFeedback || undefined,
        strengths: strengths ? strengths.split('\n').filter(s => s.trim()) : undefined,
        improvements: improvements ? improvements.split('\n').filter(s => s.trim()) : undefined,
        score_breakdown: {
          technical_knowledge: technicalKnowledge ? parseInt(technicalKnowledge) : undefined,
          problem_solving: problemSolving ? parseInt(problemSolving) : undefined,
          communication: communication ? parseInt(communication) : undefined,
          code_quality: codeQuality ? parseInt(codeQuality) : undefined,
          engagement: engagement ? parseInt(engagement) : undefined,
        },
        skill_breakdown: Object.keys(skillsAssessment).length > 0
          ? Object.entries(skillsAssessment).reduce((acc, [skillName, data]) => {
              acc[skillName] = {
                score: parseInt(data.score) || 0,
                feedback: data.feedback,
                proficiency_level: data.proficiency,
              };
              return acc;
            }, {} as Record<string, any>)
          : undefined,
      };

      await submitTrainerReview(submission.id, {
        trainer_score: score,
        trainer_evaluation: trainerEvaluation,
      });

      // Show success toast
      toast.success('Review submitted successfully', {
        description: `Submission #${submission.id} has been graded with score: ${score}`,
      });

      if (onReviewSuccess) {
        onReviewSuccess();
      }
    } catch (err) {
      console.error('Failed to submit review:', err);
      setError(err instanceof Error ? err.message : 'Failed to submit review');
      setSubmitting(false);
    }
  };

  const updateSkillScore = (skillName: string, field: 'score' | 'feedback' | 'proficiency', value: string) => {
    setSkillsAssessment(prev => ({
      ...prev,
      [skillName]: {
        ...prev[skillName],
        [field]: value,
      },
    }));
  };

  if (!submission) return null;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full overflow-y-auto bg-white/95 sm:max-w-[90vw] lg:max-w-[80vw]"
      >
        <SheetTitle className="sr-only">Review Submission #{submission.id}</SheetTitle>
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 sm:px-6 pb-16">
          <header className="space-y-4 pt-4">
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="secondary">Submission #{submission.id}</Badge>
                <Badge variant="outline">Test ID: {submission.test_id}</Badge>
                <Badge>Status: {submission.status}</Badge>
                {readOnly && <Badge variant="default" className="bg-blue-600">Read-Only View</Badge>}
              </div>
              <h2 className="text-3xl font-semibold text-slate-900">
                {details?.test?.name || 'Loading...'}
              </h2>
              <p className="max-w-2xl text-sm text-slate-500">
                {readOnly
                  ? 'Viewing previously submitted trainer review. This submission has already been graded.'
                  : 'Review the interview transcript and AI evaluation, then provide your comprehensive assessment.'}
              </p>
            </div>
          </header>

          {error && (
            <Card className="border-red-200 bg-red-50">
              <CardContent className="pt-6">
                <p className="text-sm text-red-800">
                  <strong>Error:</strong> {error}
                </p>
              </CardContent>
            </Card>
          )}

          {loading ? (
            <div className="flex h-48 items-center justify-center text-sm text-slate-500">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Loading interview details…
            </div>
          ) : details ? (
            <Tabs defaultValue="review" className="w-full">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="review">{readOnly ? 'Trainer Review' : 'Your Review'}</TabsTrigger>
                <TabsTrigger value="ai-evaluation">AI Evaluation</TabsTrigger>
                <TabsTrigger value="transcript">Transcript</TabsTrigger>
              </TabsList>

              <TabsContent value="review" className="space-y-4">
                {readOnly && details.transcript?.trainer_evaluation ? (
                  // Read-only display of trainer review (similar to AI evaluation style)
                  <ScrollArea className="h-[calc(100vh-300px)]">
                    <div className="space-y-4 pr-4">
                      <Card>
                        <CardHeader>
                          <CardTitle>Trainer Overall Score</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="flex items-center gap-4">
                            <div className="text-4xl font-bold text-slate-900">
                              {details.transcript.trainer_evaluation.overall_score}
                            </div>
                            <div className="text-sm text-slate-500">out of 100</div>
                          </div>
                        </CardContent>
                      </Card>

                      {details.transcript.trainer_evaluation.score_breakdown && Object.keys(details.transcript.trainer_evaluation.score_breakdown).length > 0 && (
                        <Card>
                          <CardHeader>
                            <CardTitle>Trainer Score Breakdown</CardTitle>
                          </CardHeader>
                          <CardContent className="space-y-3">
                            {Object.entries(details.transcript.trainer_evaluation.score_breakdown).map(
                              ([key, value]) => (
                                <div key={key} className="flex items-center justify-between">
                                  <span className="text-sm capitalize text-slate-700">
                                    {key.replace(/_/g, ' ')}
                                  </span>
                                  <Badge variant="outline">{value}/100</Badge>
                                </div>
                              ),
                            )}
                          </CardContent>
                        </Card>
                      )}

                      <Card>
                        <CardHeader>
                          <CardTitle>Trainer Feedback</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                          {details.transcript.trainer_evaluation.feedback && (
                            <div>
                              <h4 className="mb-2 font-medium text-slate-900">Overall Assessment</h4>
                              <p className="text-sm text-slate-600 whitespace-pre-wrap">
                                {details.transcript.trainer_evaluation.feedback}
                              </p>
                            </div>
                          )}

                          {details.transcript.trainer_evaluation.strengths && details.transcript.trainer_evaluation.strengths.length > 0 && (
                            <div>
                              <h4 className="mb-2 font-medium text-green-700">Strengths</h4>
                              <ul className="list-disc space-y-1 pl-5">
                                {details.transcript.trainer_evaluation.strengths.map((item, idx) => (
                                  <li key={idx} className="text-sm text-slate-600">
                                    {item}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {details.transcript.trainer_evaluation.improvements && details.transcript.trainer_evaluation.improvements.length > 0 && (
                            <div>
                              <h4 className="mb-2 font-medium text-orange-700">Areas for Improvement</h4>
                              <ul className="list-disc space-y-1 pl-5">
                                {details.transcript.trainer_evaluation.improvements.map((item, idx) => (
                                  <li key={idx} className="text-sm text-slate-600">
                                    {item}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </CardContent>
                      </Card>

                      {details.transcript.trainer_evaluation.skill_breakdown && Object.keys(details.transcript.trainer_evaluation.skill_breakdown).length > 0 && (
                        <Card>
                          <CardHeader>
                            <CardTitle>Trainer Skills Assessment</CardTitle>
                          </CardHeader>
                          <CardContent className="space-y-4">
                            {Object.entries(details.transcript.trainer_evaluation.skill_breakdown).map(([skillName, skill]) => (
                              <div key={skillName} className="rounded-lg border border-slate-200 bg-slate-50/50 p-4">
                                <div className="mb-2 flex items-center justify-between">
                                  <span className="font-semibold text-slate-900">{skillName}</span>
                                  <div className="flex items-center gap-2">
                                    <Badge variant="outline">{skill.proficiency_level}</Badge>
                                    <span className="text-sm font-medium text-slate-700">{Math.round(skill.score)}%</span>
                                  </div>
                                </div>
                                <p className="text-sm text-slate-600">{skill.feedback}</p>
                              </div>
                            ))}
                          </CardContent>
                        </Card>
                      )}
                    </div>
                  </ScrollArea>
                ) : (
                  // Editable form for trainer review
                <ScrollArea className="h-[calc(100vh-300px)]">
                  <div className="space-y-6 pr-4">
                    {/* Overall Score */}
                    <Card>
                      <CardHeader>
                        <CardTitle>Overall Score</CardTitle>
                        <CardDescription>{readOnly ? 'Final assessment score' : 'Your final assessment score (0-100)'}</CardDescription>
                      </CardHeader>
                      <CardContent>
                        <div className="flex items-end gap-2">
                          <div className="flex-1">
                            <Input
                              type="number"
                              min="0"
                              max="100"
                              value={trainerScore}
                              onChange={(e) => setTrainerScore(e.target.value)}
                              placeholder={details.transcript?.lambda_evaluation?.overall_score ? `AI suggested: ${details.transcript.lambda_evaluation.overall_score}` : "Enter score"}
                              className="text-lg placeholder:text-slate-400"
                              disabled={readOnly}
                            />
                          </div>
                          {!readOnly && details.transcript?.lambda_evaluation?.overall_score && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => setTrainerScore(details.transcript.lambda_evaluation!.overall_score.toString())}
                            >
                              <Lightbulb className="mr-2 h-4 w-4" />
                              Use AI: {details.transcript.lambda_evaluation.overall_score}
                            </Button>
                          )}
                        </div>
                      </CardContent>
                    </Card>

                    {/* Performance Breakdown */}
                    <Card>
                      <CardHeader>
                        <CardTitle>Performance Breakdown</CardTitle>
                        <CardDescription>{readOnly ? 'Score for each dimension' : 'Score each dimension (0-100)'}</CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        {[
                          { label: 'Technical Knowledge', state: technicalKnowledge, setState: setTechnicalKnowledge, aiKey: 'technical_knowledge' },
                          { label: 'Problem Solving', state: problemSolving, setState: setProblemSolving, aiKey: 'problem_solving' },
                          { label: 'Communication', state: communication, setState: setCommunication, aiKey: 'communication' },
                          { label: 'Code Quality', state: codeQuality, setState: setCodeQuality, aiKey: 'code_quality' },
                          { label: 'Engagement', state: engagement, setState: setEngagement, aiKey: 'engagement' },
                        ].map(({ label, state, setState, aiKey }) => (
                          <div key={label} className="space-y-2">
                            <Label>{label}</Label>
                            <div className="flex items-center gap-2">
                              <Input
                                type="number"
                                min="0"
                                max="100"
                                value={state}
                                onChange={(e) => setState(e.target.value)}
                                placeholder={details.transcript?.lambda_evaluation?.score_breakdown[aiKey as keyof typeof details.transcript.lambda_evaluation.score_breakdown] ? `AI: ${details.transcript.lambda_evaluation.score_breakdown[aiKey as keyof typeof details.transcript.lambda_evaluation.score_breakdown]}` : "Score"}
                                className="placeholder:text-slate-400"
                                disabled={readOnly}
                              />
                              {!readOnly && details.transcript?.lambda_evaluation?.score_breakdown[aiKey as keyof typeof details.transcript.lambda_evaluation.score_breakdown] && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => setState(details.transcript.lambda_evaluation!.score_breakdown[aiKey as keyof typeof details.transcript.lambda_evaluation.score_breakdown]!.toString())}
                                >
                                  <Copy className="mr-1 h-3 w-3" />
                                  AI: {details.transcript.lambda_evaluation.score_breakdown[aiKey as keyof typeof details.transcript.lambda_evaluation.score_breakdown]}
                                </Button>
                              )}
                            </div>
                          </div>
                        ))}
                      </CardContent>
                    </Card>

                    {/* Skills Assessment */}
                    {details.transcript?.lambda_evaluation?.skill_breakdown && Object.keys(details.transcript.lambda_evaluation.skill_breakdown).length > 0 && (
                      <Card>
                        <CardHeader>
                          <CardTitle>Skills Assessment</CardTitle>
                          <CardDescription>Evaluate proficiency for each skill</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-6">
                          {Object.entries(details.transcript.lambda_evaluation.skill_breakdown).map(([skillName, aiSkill]) => (
                            <div key={skillName} className="space-y-3 rounded-lg border border-slate-200 bg-slate-50/50 p-4">
                              <h4 className="font-semibold text-slate-900">{skillName}</h4>

                              <div className="grid grid-cols-2 gap-3">
                                <div className="space-y-2">
                                  <Label className="text-xs">Score (0-100)</Label>
                                  <div className="flex items-center gap-2">
                                    <Input
                                      type="number"
                                      min="0"
                                      max="100"
                                      value={skillsAssessment[skillName]?.score || ''}
                                      onChange={(e) => updateSkillScore(skillName, 'score', e.target.value)}
                                      placeholder={`AI: ${aiSkill.score}`}
                                      className="text-sm placeholder:text-slate-400"
                                      disabled={readOnly}
                                    />
                                    {!readOnly && (
                                      <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => updateSkillScore(skillName, 'score', aiSkill.score.toString())}
                                      >
                                        <Copy className="h-3 w-3" />
                                      </Button>
                                    )}
                                  </div>
                                </div>

                                <div className="space-y-2">
                                  <Label className="text-xs">Proficiency Level</Label>
                                  <div className="flex items-center gap-2">
                                    <select
                                      value={skillsAssessment[skillName]?.proficiency || ''}
                                      onChange={(e) => updateSkillScore(skillName, 'proficiency', e.target.value)}
                                      className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm text-slate-900 [&>option:first-child]:text-slate-400"
                                      disabled={readOnly}
                                    >
                                      <option value="" className="text-slate-400">AI: {aiSkill.proficiency_level}</option>
                                      <option value="EXPERT">EXPERT</option>
                                      <option value="PROFICIENT">PROFICIENT</option>
                                      <option value="COMPETENT">COMPETENT</option>
                                      <option value="BASIC">BASIC</option>
                                      <option value="INSUFFICIENT">INSUFFICIENT</option>
                                    </select>
                                    {!readOnly && (
                                      <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => updateSkillScore(skillName, 'proficiency', aiSkill.proficiency_level)}
                                      >
                                        <Copy className="h-3 w-3" />
                                      </Button>
                                    )}
                                  </div>
                                </div>
                              </div>

                              <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                  <Label className="text-xs">Feedback</Label>
                                  {!readOnly && (
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      onClick={() => updateSkillScore(skillName, 'feedback', aiSkill.feedback)}
                                    >
                                      <Copy className="mr-1 h-3 w-3" />
                                      Use AI
                                    </Button>
                                  )}
                                </div>
                                <Textarea
                                  value={skillsAssessment[skillName]?.feedback || ''}
                                  onChange={(e) => updateSkillScore(skillName, 'feedback', e.target.value)}
                                  placeholder={aiSkill.feedback ? `AI: ${aiSkill.feedback}` : "Detailed feedback for this skill..."}
                                  rows={2}
                                  className="text-sm placeholder:text-slate-400"
                                  disabled={readOnly}
                                />
                              </div>
                            </div>
                          ))}
                        </CardContent>
                      </Card>
                    )}

                    {/* Overall Feedback */}
                    <Card>
                      <CardHeader>
                        <div className="flex items-center justify-between">
                          <div>
                            <CardTitle>Overall Feedback</CardTitle>
                            <CardDescription>{readOnly ? 'Trainer assessment' : 'Comprehensive assessment of the interview'}</CardDescription>
                          </div>
                          {!readOnly && details.transcript?.lambda_evaluation?.feedback && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleUseAIValue(setOverallFeedback, details.transcript.lambda_evaluation?.feedback)}
                            >
                              <Lightbulb className="mr-2 h-4 w-4" />
                              Use AI Feedback
                            </Button>
                          )}
                        </div>
                      </CardHeader>
                      <CardContent>
                        <Textarea
                          value={overallFeedback}
                          onChange={(e) => setOverallFeedback(e.target.value)}
                          placeholder={details.transcript?.lambda_evaluation?.feedback ? `AI: ${details.transcript.lambda_evaluation.feedback}` : "Provide your overall feedback and assessment..."}
                          rows={6}
                          className="placeholder:text-slate-400"
                          disabled={readOnly}
                        />
                      </CardContent>
                    </Card>

                    {/* Strengths */}
                    <Card>
                      <CardHeader>
                        <div className="flex items-center justify-between">
                          <div>
                            <CardTitle>Strengths</CardTitle>
                            <CardDescription>One strength per line</CardDescription>
                          </div>
                          {!readOnly && details.transcript?.lambda_evaluation?.strengths && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleUseAIValue(setStrengths, details.transcript.lambda_evaluation?.strengths)}
                            >
                              <Lightbulb className="mr-2 h-4 w-4" />
                              Use AI Strengths
                            </Button>
                          )}
                        </div>
                      </CardHeader>
                      <CardContent>
                        <Textarea
                          value={strengths}
                          onChange={(e) => setStrengths(e.target.value)}
                          placeholder={details.transcript?.lambda_evaluation?.strengths?.length ? `AI: ${details.transcript.lambda_evaluation.strengths.slice(0, 2).join(' | ')}${details.transcript.lambda_evaluation.strengths.length > 2 ? '...' : ''}` : "Enter strengths (one per line)&#10;Example:&#10;Strong problem-solving skills&#10;Clear communication"}
                          rows={5}
                          className="placeholder:text-slate-400"
                          disabled={readOnly}
                        />
                      </CardContent>
                    </Card>

                    {/* Areas for Improvement */}
                    <Card>
                      <CardHeader>
                        <div className="flex items-center justify-between">
                          <div>
                            <CardTitle>Areas for Improvement</CardTitle>
                            <CardDescription>One area per line</CardDescription>
                          </div>
                          {!readOnly && details.transcript?.lambda_evaluation?.improvements && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleUseAIValue(setImprovements, details.transcript.lambda_evaluation?.improvements)}
                            >
                              <Lightbulb className="mr-2 h-4 w-4" />
                              Use AI Suggestions
                            </Button>
                          )}
                        </div>
                      </CardHeader>
                      <CardContent>
                        <Textarea
                          value={improvements}
                          onChange={(e) => setImprovements(e.target.value)}
                          placeholder={details.transcript?.lambda_evaluation?.improvements?.length ? `AI: ${details.transcript.lambda_evaluation.improvements.slice(0, 2).join(' | ')}${details.transcript.lambda_evaluation.improvements.length > 2 ? '...' : ''}` : "Enter areas for improvement (one per line)&#10;Example:&#10;Could provide more detailed explanations&#10;Consider edge cases more thoroughly"}
                          rows={5}
                          className="placeholder:text-slate-400"
                          disabled={readOnly}
                        />
                      </CardContent>
                    </Card>

                    {/* Submit Button - Hidden in read-only mode */}
                    {!readOnly && (
                      <Button
                        className="w-full"
                        onClick={handleSubmit}
                        disabled={!trainerScore || submitting}
                        size="lg"
                      >
                        {submitting ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Submitting Review...
                          </>
                        ) : (
                          <>
                            <CheckCircle2 className="mr-2 h-4 w-4" />
                            Submit Review
                          </>
                        )}
                      </Button>
                    )}
                  </div>
                </ScrollArea>
                )}
              </TabsContent>

              <TabsContent value="ai-evaluation" className="space-y-4">
                {details.transcript?.lambda_evaluation ? (
                  <ScrollArea className="h-[calc(100vh-300px)]">
                    <div className="space-y-4 pr-4">
                      <Card>
                        <CardHeader>
                          <CardTitle>AI Overall Score</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="flex items-center gap-4">
                            <div className="text-4xl font-bold text-slate-900">
                              {details.transcript.lambda_evaluation.overall_score}
                            </div>
                            <div className="text-sm text-slate-500">out of 100</div>
                          </div>
                          <p className="mt-4 text-sm text-slate-600">
                            Recommendation:{' '}
                            <Badge>{details.transcript.lambda_evaluation.recommendation}</Badge>
                          </p>
                          {details.transcript.lambda_evaluation.reasoning && (
                            <p className="mt-2 text-sm text-slate-600">
                              {details.transcript.lambda_evaluation.reasoning}
                            </p>
                          )}
                        </CardContent>
                      </Card>

                      <Card>
                        <CardHeader>
                          <CardTitle>AI Score Breakdown</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-3">
                          {Object.entries(details.transcript.lambda_evaluation.score_breakdown).map(
                            ([key, value]) => (
                              <div key={key} className="flex items-center justify-between">
                                <span className="text-sm capitalize text-slate-700">
                                  {key.replace(/_/g, ' ')}
                                </span>
                                <Badge variant="outline">{value}/100</Badge>
                              </div>
                            ),
                          )}
                        </CardContent>
                      </Card>

                      <Card>
                        <CardHeader>
                          <CardTitle>AI Feedback</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                          <div>
                            <h4 className="mb-2 font-medium text-slate-900">Overall Assessment</h4>
                            <p className="text-sm text-slate-600">
                              {details.transcript.lambda_evaluation.feedback}
                            </p>
                          </div>

                          {details.transcript.lambda_evaluation.strengths.length > 0 && (
                            <div>
                              <h4 className="mb-2 font-medium text-green-700">Strengths</h4>
                              <ul className="list-disc space-y-1 pl-5">
                                {details.transcript.lambda_evaluation.strengths.map((item, idx) => (
                                  <li key={idx} className="text-sm text-slate-600">
                                    {item}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {details.transcript.lambda_evaluation.improvements.length > 0 && (
                            <div>
                              <h4 className="mb-2 font-medium text-orange-700">Areas for Improvement</h4>
                              <ul className="list-disc space-y-1 pl-5">
                                {details.transcript.lambda_evaluation.improvements.map((item, idx) => (
                                  <li key={idx} className="text-sm text-slate-600">
                                    {item}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {details.transcript.lambda_evaluation.key_highlights.length > 0 && (
                            <div>
                              <h4 className="mb-2 font-medium text-blue-700">Key Highlights</h4>
                              <ul className="list-disc space-y-1 pl-5">
                                {details.transcript.lambda_evaluation.key_highlights.map((item, idx) => (
                                  <li key={idx} className="text-sm text-slate-600">
                                    {item}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {details.transcript.lambda_evaluation.red_flags.length > 0 && (
                            <div>
                              <h4 className="mb-2 font-medium text-red-700">Red Flags</h4>
                              <ul className="list-disc space-y-1 pl-5">
                                {details.transcript.lambda_evaluation.red_flags.map((item, idx) => (
                                  <li key={idx} className="text-sm text-slate-600">
                                    {item}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </CardContent>
                      </Card>

                      {Object.keys(details.transcript.lambda_evaluation.skill_breakdown).length > 0 && (
                        <Card>
                          <CardHeader>
                            <CardTitle>AI Skills Assessment</CardTitle>
                          </CardHeader>
                          <CardContent className="space-y-4">
                            {Object.entries(details.transcript.lambda_evaluation.skill_breakdown).map(([skillName, skill]) => (
                              <div key={skillName} className="rounded-lg border border-slate-200 bg-slate-50/50 p-4">
                                <div className="mb-2 flex items-center justify-between">
                                  <span className="font-semibold text-slate-900">{skillName}</span>
                                  <div className="flex items-center gap-2">
                                    <Badge variant="outline">{skill.proficiency_level}</Badge>
                                    <span className="text-sm font-medium text-slate-700">{Math.round(skill.score)}%</span>
                                  </div>
                                </div>
                                <p className="text-sm text-slate-600">{skill.feedback}</p>
                              </div>
                            ))}
                          </CardContent>
                        </Card>
                      )}
                    </div>
                  </ScrollArea>
                ) : (
                  <Card>
                    <CardContent className="pt-6">
                      <p className="text-sm text-slate-500">No AI evaluation available.</p>
                    </CardContent>
                  </Card>
                )}
              </TabsContent>

              <TabsContent value="transcript" className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle>Interview Transcript</CardTitle>
                    <CardDescription>
                      {details.transcript ? (
                        <>
                          {details.transcript.message_count} messages •{' '}
                          {Math.round((details.transcript.duration_seconds || 0) / 60)} minutes
                        </>
                      ) : (
                        'Transcript not available'
                      )}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    {!details.transcript ? (
                      <div className="flex h-[calc(100vh-350px)] items-center justify-center text-muted-foreground">
                        <div className="text-center">
                          <p className="text-lg font-medium">Transcript Not Available</p>
                          <p className="text-sm">The interview transcript could not be loaded.</p>
                        </div>
                      </div>
                    ) : (
                      <ScrollArea className="h-[calc(100vh-350px)]">
                        <div className="space-y-4 pr-4">
                          {details.transcript.messages.map((message, idx) => (
                          <div
                            key={idx}
                            className={`rounded-lg border p-4 ${
                              message.role === 'user'
                                ? 'border-blue-200 bg-blue-50/50'
                                : 'border-slate-200 bg-slate-50/50'
                            }`}
                          >
                            <div className="mb-2 flex items-center justify-between">
                              <Badge variant={message.role === 'user' ? 'default' : 'secondary'}>
                                {message.role === 'user' ? 'Participant' : 'AI Interviewer'}
                              </Badge>
                              {getAudioUrlForMessage(idx) && (
                                <div className="flex items-center gap-2">
                                  {playingAudioIndex === idx && (
                                    <>
                                      {/* Progress indicator */}
                                      <div className="flex items-center gap-1 text-xs text-slate-600">
                                        <span>{Math.floor(audioPlayer.currentTime)}s</span>
                                        <span>/</span>
                                        <span>{Math.floor(audioPlayer.duration)}s</span>
                                      </div>
                                      {/* Progress bar - clickable timeline scrubber */}
                                      <div
                                        className="h-2 w-32 rounded-full bg-slate-200 overflow-hidden cursor-pointer hover:bg-slate-300 transition-colors"
                                        onClick={(e) => {
                                          const rect = e.currentTarget.getBoundingClientRect();
                                          const clickX = e.clientX - rect.left;
                                          const percentage = (clickX / rect.width) * 100;
                                          const seekTime = (percentage / 100) * audioPlayer.duration;
                                          audioPlayer.seek(seekTime);
                                        }}
                                        title="Click to seek"
                                      >
                                        <div
                                          className="h-full bg-blue-600 transition-all duration-100 pointer-events-none"
                                          style={{ width: `${audioPlayer.progress}%` }}
                                        />
                                      </div>
                                    </>
                                  )}
                                  {/* Play/Pause button */}
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    onClick={() => handlePlayAudio(getAudioUrlForMessage(idx)!, idx)}
                                  >
                                    {playingAudioIndex === idx && audioPlayer.isPlaying ? (
                                      <>
                                        <Pause className="mr-1 h-3 w-3" />
                                        Pause
                                      </>
                                    ) : playingAudioIndex === idx && audioPlayer.isPaused ? (
                                      <>
                                        <Play className="mr-1 h-3 w-3" />
                                        Resume
                                      </>
                                    ) : (
                                      <>
                                        <Play className="mr-1 h-3 w-3" />
                                        Play
                                      </>
                                    )}
                                  </Button>
                                  {/* Restart button (only show when this audio is active) */}
                                  {playingAudioIndex === idx && (
                                    <Button
                                      size="sm"
                                      variant="ghost"
                                      onClick={handleRestartAudio}
                                      title="Restart audio"
                                    >
                                      <RotateCcw className="h-3 w-3" />
                                    </Button>
                                  )}
                                </div>
                              )}
                            </div>
                            <p className="text-sm text-slate-700 whitespace-pre-wrap">
                              {message.content}
                            </p>
                            <p className="mt-2 text-xs text-slate-400">
                              {new Date(message.timestamp).toLocaleString()}
                            </p>
                          </div>
                        ))}
                      </div>
                    </ScrollArea>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          ) : null}
        </div>
      </SheetContent>
    </Sheet>
  );
}
