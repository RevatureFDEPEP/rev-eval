"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  BookOpen,
  ChevronDown,
  Filter,
  PlusCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { getQuestions, Question, QuestionType } from "@/lib/api";
import { QuestionDetailsSheet } from "@/components/trainer/QuestionDetailsSheet";
import { formatRelativeTime } from "@/lib/utils/date";

export default function QuestionsPage() {
  const router = useRouter();
  const [questions, setQuestions] = useState<Question[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedQuestion, setSelectedQuestion] = useState<Question | null>(
    null
  );
  const [sheetOpen, setSheetOpen] = useState(false);
  const [skillFilter, setSkillFilter] = useState<string>("all");

  // Load questions
  const loadQuestions = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getQuestions();
      setQuestions(data);
    } catch (err: any) {
      console.error("Failed to load questions:", err);
      setError(err.message || "Failed to load questions");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadQuestions();
  }, [loadQuestions]);

  // Get unique skills from all questions
  const allSkills = useMemo(() => {
    const skillSet = new Set<string>();
    questions.forEach((q) => q.skills.forEach((s) => skillSet.add(s)));
    return Array.from(skillSet).sort();
  }, [questions]);

  // Filter questions by skill
  const filteredQuestions = useMemo(() => {
    if (skillFilter === "all") return questions;
    return questions.filter((q) => q.skills.includes(skillFilter));
  }, [questions, skillFilter]);

  // Calculate stats
  const stats = useMemo(() => {
    const total = questions.length;
    const byType = {
      mcq: questions.filter((q) => q.type === "mcq").length,
      multi: questions.filter((q) => q.type === "multi").length,
      true_false: questions.filter((q) => q.type === "true_false").length,
      text: questions.filter((q) => q.type === "text").length,
    };
    return { total, byType };
  }, [questions]);

  const handleQuestionClick = (question: Question) => {
    setSelectedQuestion(question);
    setSheetOpen(true);
  };

  const handleQuestionDeleted = () => {
    loadQuestions();
  };

  const getTypeColor = (type: QuestionType) => {
    switch (type) {
      case "mcq":
        return "bg-blue-100 text-blue-700 hover:bg-blue-200";
      case "multi":
        return "bg-purple-100 text-purple-700 hover:bg-purple-200";
      case "true_false":
        return "bg-green-100 text-green-700 hover:bg-green-200";
      case "text":
        return "bg-orange-100 text-orange-700 hover:bg-orange-200";
    }
  };

  const getTypeLabel = (type: QuestionType) => {
    switch (type) {
      case "mcq":
        return "Single Choice";
      case "multi":
        return "Multiple Choice";
      case "true_false":
        return "True/False";
      case "text":
        return "Text Answer";
    }
  };

  const getDifficultyColor = (difficulty?: string) => {
    switch (difficulty) {
      case "easy":
        return "bg-green-100 text-green-700";
      case "medium":
        return "bg-yellow-100 text-yellow-700";
      case "hard":
        return "bg-red-100 text-red-700";
      default:
        return "bg-slate-100 text-slate-700";
    }
  };

  if (loading) {
    return (
      <div className="flex h-[calc(100vh-200px)] items-center justify-center">
        <div className="text-center">
          <div className="mx-auto h-8 w-8 animate-spin rounded-full border-b-2 border-slate-900" />
          <p className="mt-2 text-sm text-slate-600">Loading questions...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-[calc(100vh-200px)] items-center justify-center">
        <Card className="border-red-200 bg-red-50/50">
          <CardContent className="py-6 text-center">
            <p className="text-sm text-red-600">{error}</p>
            <Button onClick={loadQuestions} variant="outline" className="mt-4">
              Try Again
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <>
      <div className="container mx-auto space-y-8 px-4 py-8">
        {/* Header */}
        <section className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-slate-500">
              <span>Trainer workspace</span>
              <span className="hidden h-1 w-1 rounded-full bg-slate-300 sm:inline" />
              <span className="text-slate-400">Questions</span>
            </div>
            <h1 className="text-3xl font-semibold text-slate-900">Question Bank</h1>
            <p className="max-w-2xl text-sm text-slate-500">
              Manage your assessment questions
            </p>
          </div>
          <Badge variant="secondary" className="rounded-full px-4 py-1 text-xs font-semibold">
            Trainer
          </Badge>
        </section>

        {/* Stats Cards */}
        <div className="grid gap-4 md:grid-cols-5">
          <Card className="border-orange-100/70 bg-gradient-to-br from-orange-50/80 via-white to-purple-50/70 shadow-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-slate-600">
                Total Questions
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-slate-900">
                {stats.total}
              </div>
            </CardContent>
          </Card>
          <Card className="border-blue-100/70 bg-blue-50/50 shadow-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-slate-600">
                Single Choice
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-700">
                {stats.byType.mcq}
              </div>
            </CardContent>
          </Card>
          <Card className="border-purple-100/70 bg-purple-50/50 shadow-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-slate-600">
                Multiple Choice
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-purple-700">
                {stats.byType.multi}
              </div>
            </CardContent>
          </Card>
          <Card className="border-green-100/70 bg-green-50/50 shadow-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-slate-600">
                True/False
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-700">
                {stats.byType.true_false}
              </div>
            </CardContent>
          </Card>
          <Card className="border-orange-100/70 bg-orange-50/50 shadow-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-slate-600">
                Text Answer
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-orange-700">
                {stats.byType.text}
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="space-y-1">
            <h2 className="text-lg font-semibold text-slate-900">Questions Overview</h2>
            <p className="text-sm text-slate-500">Browse, filter, and reuse your assessment prompts.</p>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button className="bg-orange-500 transition-transform hover:-translate-y-0.5 hover:bg-orange-600">
                <PlusCircle className="mr-2 size-4" />
                Create Question
                <ChevronDown className="ml-2 size-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel>Select Question Type</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => router.push("/trainer/questions/create?type=mcq")}>
                <div className="flex flex-col gap-1">
                  <div className="font-medium">MCQ</div>
                  <div className="text-xs text-slate-500">Multiple choice with one or more correct answers</div>
                </div>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => router.push("/trainer/questions/create?type=true_false")}>
                <div className="flex flex-col gap-1">
                  <div className="font-medium">True/False</div>
                  <div className="text-xs text-slate-500">Simple true or false question</div>
                </div>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => router.push("/trainer/questions/create?type=text")}>
                <div className="flex flex-col gap-1">
                  <div className="font-medium">Text Answer</div>
                  <div className="text-xs text-slate-500">Free-form text response</div>
                </div>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        {/* Filters */}
        {allSkills.length > 0 && (
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Filter className="size-4 text-slate-500" />
              <span className="text-sm font-medium text-slate-700">
                Filter by Skill:
              </span>
            </div>
            <Select value={skillFilter} onValueChange={setSkillFilter}>
              <SelectTrigger className="w-[250px]">
                <SelectValue placeholder="All Skills" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Skills</SelectItem>
                {allSkills.map((skill) => (
                  <SelectItem key={skill} value={skill}>
                    {skill}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {skillFilter !== "all" && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSkillFilter("all")}
              >
                Clear Filter
              </Button>
            )}
          </div>
        )}

        {/* Questions Table */}
        {filteredQuestions.length === 0 ? (
          <Card className="border-dashed">
            <CardContent className="flex flex-col items-center justify-center gap-4 py-12 text-center">
              <div className="rounded-full bg-slate-100 p-3">
                <BookOpen className="size-6 text-slate-400" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-slate-900">
                  {skillFilter !== "all"
                    ? "No questions found with this skill"
                    : "No questions yet"}
                </h3>
                <p className="text-sm text-slate-500">
                  {skillFilter !== "all"
                    ? "Try selecting a different skill filter"
                    : "Start by creating your first question"}
                </p>
              </div>
              {skillFilter === "all" && (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button>
                      <PlusCircle className="mr-2 size-4" />
                      Create your first question
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="center" className="w-56">
                    <DropdownMenuLabel>Select Question Type</DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      onClick={() =>
                        router.push("/trainer/questions/create?type=mcq")
                      }
                    >
                      MCQ
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() =>
                        router.push("/trainer/questions/create?type=true_false")
                      }
                    >
                      True/False
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() =>
                        router.push("/trainer/questions/create?type=text")
                      }
                    >
                      Text Answer
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              )}
            </CardContent>
          </Card>
        ) : (
          <Card className="border-slate-200/80 shadow-sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BookOpen className="size-5 text-orange-400" />
                Questions ({filteredQuestions.length})
              </CardTitle>
              <CardDescription>
                Click on a question to view details
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Question</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Difficulty</TableHead>
                    <TableHead>Skills</TableHead>
                    <TableHead>Created</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredQuestions.map((question, index) => (
                    <TableRow
                      key={question.id || `question-${index}`}
                      onClick={() => handleQuestionClick(question)}
                      className="cursor-pointer transition-transform hover:-translate-y-[1px] hover:bg-orange-50/60"
                    >
                      <TableCell className="max-w-md font-medium">
                        <div className="truncate">
                          {question.question_text.length > 80
                            ? `${question.question_text.slice(0, 80)}...`
                            : question.question_text}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="secondary"
                          className={getTypeColor(question.type)}
                        >
                          {getTypeLabel(question.type)}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {question.difficulty ? (
                          <Badge
                            variant="secondary"
                            className={getDifficultyColor(question.difficulty)}
                          >
                            {question.difficulty}
                          </Badge>
                        ) : (
                          <span className="text-sm text-slate-400">—</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {question.skills.slice(0, 2).map((skill, idx) => (
                            <Badge
                              key={`${question.id}-skill-${idx}`}
                              variant="outline"
                              className="text-xs"
                            >
                              {skill}
                            </Badge>
                          ))}
                          {question.skills.length > 2 && (
                            <Badge
                              variant="outline"
                              className="text-xs text-slate-500"
                            >
                              +{question.skills.length - 2} more
                            </Badge>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-sm text-slate-500">
                        {formatRelativeTime(question.created_at)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Question Details Sheet */}
      {selectedQuestion && (
        <QuestionDetailsSheet
          question={selectedQuestion}
          open={sheetOpen}
          onOpenChange={(open) => {
            setSheetOpen(open);
            if (!open) {
              setSelectedQuestion(null);
            }
          }}
          onDelete={handleQuestionDeleted}
        />
      )}
    </>
  );
}
