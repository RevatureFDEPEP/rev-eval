'use client';

import { useEffect, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { getSubmissionReviewDetails } from '@/lib/api';
import type { TestSubmission } from '@/lib/api/types';
import { Loader2, Play, Pause, RotateCcw } from 'lucide-react';
import { useAudioPlayer } from '@/lib/hooks/useAudioPlayer';
import { formatTableDate } from '@/lib/utils/date';
import { Button } from '@/components/ui/button';

interface GradedSubmissionSheetProps {
  submission: TestSubmission | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
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
  };
}

export function GradedSubmissionSheet({
  submission,
  open,
  onOpenChange,
}: GradedSubmissionSheetProps) {
  const [details, setDetails] = useState<ReviewDetails | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [playingAudioIndex, setPlayingAudioIndex] = useState<number | null>(null);
  const audioPlayer = useAudioPlayer();

  useEffect(() => {
    if (!submission || !open) {
      setDetails(null);
      setError(null);
      return;
    }

    const loadDetails = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await getSubmissionReviewDetails(submission.id);
        setDetails(data);
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
    if (playingAudioIndex === messageIndex && audioPlayer.isPlaying) {
      audioPlayer.pause();
      return;
    }

    if (playingAudioIndex === messageIndex && audioPlayer.isPaused) {
      audioPlayer.resume();
      return;
    }

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

  if (!submission) return null;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full overflow-y-auto bg-white/95 sm:max-w-[90vw] lg:max-w-[80vw]"
      >
        <SheetTitle className="sr-only">Graded Submission #{submission.id}</SheetTitle>
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 sm:px-6 pb-16">
          <header className="space-y-4 pt-4">
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="secondary">Submission #{submission.id}</Badge>
                <Badge variant="outline">Test ID: {submission.test_id}</Badge>
                <Badge>Status: {submission.status}</Badge>
                <Badge variant="default" className="bg-green-600">Graded</Badge>
              </div>
              <h2 className="text-3xl font-semibold text-slate-900">
                {details?.test?.name || 'Loading...'}
              </h2>
              <p className="max-w-2xl text-sm text-slate-500">
                This submission has been graded. You are viewing the final scores and feedback.
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
            <Tabs defaultValue="scores" className="w-full">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="scores">Scores & Feedback</TabsTrigger>
                <TabsTrigger value="ai-evaluation">AI Evaluation</TabsTrigger>
                <TabsTrigger value="transcript">Transcript</TabsTrigger>
              </TabsList>

              <TabsContent value="scores" className="space-y-4">
                <ScrollArea className="h-[calc(100vh-300px)]">
                  <div className="space-y-6 pr-4">
                    {/* Final Scores Card */}
                    <Card>
                      <CardHeader>
                        <CardTitle>Final Scores</CardTitle>
                        <CardDescription>Trainer-assigned and AI-generated scores</CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                            <p className="text-xs uppercase tracking-wide text-slate-500">Trainer Score</p>
                            <p className="text-3xl font-bold text-slate-900">{submission.trainer_score || 'N/A'}</p>
                          </div>
                          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                            <p className="text-xs uppercase tracking-wide text-slate-500">AI Score</p>
                            <p className="text-3xl font-bold text-slate-900">{submission.ai_score || 'N/A'}</p>
                          </div>
                        </div>
                        <div className="rounded-lg border border-green-200 bg-green-50 p-4">
                          <p className="text-xs uppercase tracking-wide text-green-700">Final Score</p>
                          <p className="text-4xl font-bold text-green-900">{submission.final_score || 'N/A'}</p>
                        </div>
                      </CardContent>
                    </Card>

                    {/* Trainer Feedback */}
                    {submission.feedback && (
                      <Card>
                        <CardHeader>
                          <CardTitle>Trainer Feedback</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <p className="whitespace-pre-wrap text-sm text-slate-700">{submission.feedback}</p>
                        </CardContent>
                      </Card>
                    )}

                    {/* Review Metadata */}
                    <Card>
                      <CardHeader>
                        <CardTitle>Review Information</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span className="text-slate-500">Reviewed At:</span>
                          <span className="text-slate-900">{submission.reviewed_at ? formatTableDate(submission.reviewed_at) : 'N/A'}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-slate-500">Reviewed By:</span>
                          <span className="text-slate-900">Trainer #{submission.reviewed_by_id}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-slate-500">Submitted At:</span>
                          <span className="text-slate-900">{submission.submitted_at ? formatTableDate(submission.submitted_at) : 'N/A'}</span>
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                </ScrollArea>
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
                                        <div className="flex items-center gap-1 text-xs text-slate-600">
                                          <span>{Math.floor(audioPlayer.currentTime)}s</span>
                                          <span>/</span>
                                          <span>{Math.floor(audioPlayer.duration)}s</span>
                                        </div>
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
            </Tabs>
          ) : null}
        </div>
      </SheetContent>
    </Sheet>
  );
}
