'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Loader2, Network, GitBranch, ChevronRight, Zap, Cpu, Brain, Eye } from 'lucide-react';

interface ToGConfig {
  search_width: number;
  search_depth: number;
  exploration_temp: number;
  reasoning_temp: number;
  num_retain_entity: number;
  pruning_method: 'llm' | 'bm25' | 'sentence_bert';
  enable_sufficiency_check: boolean;
}

interface ToGReasoningStep {
  depth: number;
  entities_explored: Array<{id: string, name: string, type: string}>;
  relations_selected: Array<{type: string, source_entity: ToGEntity, target_entity: ToGEntity, confidence: number}>;
  entity_scores?: Record<string, number>;
  sufficiency_score?: number;
  sufficient?: boolean;
  reasoning_notes?: string;
}

interface ToGEntity {
  id: string;
  name: string;
  type: string;
  description?: string;
  confidence?: number;
}

interface ToGTriplet {
  subject: string;
  relation: string;
  object: string;
  confidence?: number;
}

interface ToGQueryResponse {
  answer: string;
  reasoning_path: ToGReasoningStep[];
  retrieved_triplets: ToGTriplet[];
  confidence: number;
  processing_time_ms: number;
  query_id?: number;
  query_type: string;
}

interface ToGQueryInterfaceProps {
  accessToken?: string;
  documents?: Array<{id: string, filename: string, status: string}>;
}

export default function ToGQueryInterface({ accessToken, documents = [] }: ToGQueryInterfaceProps) {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<ToGQueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [visualization, setVisualization] = useState<any>(null);
  const [loadingVisualization, setLoadingVisualization] = useState(false);

  // ToG configuration
  const [config, setConfig] = useState<ToGConfig>({
    search_width: 3,
    search_depth: 3,
    exploration_temp: 0.4,
    reasoning_temp: 0.0,
    num_retain_entity: 5,
    pruning_method: 'llm',
    enable_sufficiency_check: true,
  });

  const [showConfig, setShowConfig] = useState(false);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([]);

  // Get completed documents
  const completedDocs = documents.filter((doc) => doc.status === 'completed');

  const loadVisualization = async (queryId: number) => {
    setLoadingVisualization(true);
    try {
      const res = await fetch(`/api/tog/visualize/${queryId}`, {
        headers: {
          ...(accessToken && { 'Authorization': `Bearer ${accessToken}` }),
        },
      });

      if (!res.ok) {
        throw new Error(`Failed to load visualization: ${res.statusText}`);
      }

      const data = await res.json();
      setVisualization(data);
    } catch (err) {
      console.error('Failed to load visualization:', err);
      setError(err instanceof Error ? err.message : 'Failed to load visualization');
    } finally {
      setLoadingVisualization(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!question.trim()) return;

    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      // First validate config
      const configRes = await fetch('/api/tog/config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(accessToken && { 'Authorization': `Bearer ${accessToken}` }),
        },
        body: JSON.stringify({
          config: config,
        }),
      });

      if (!configRes.ok) {
        throw new Error(`Config validation failed: ${configRes.statusText}`);
      }

      const configValidation = await configRes.json();
      if (!configValidation.is_valid) {
        throw new Error(`Invalid config: ${configValidation.validation_errors.join(', ')}`);
      }

      // Then submit query
      const res = await fetch('/api/tog/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(accessToken && { 'Authorization': `Bearer ${accessToken}` }),
        },
        body: JSON.stringify({
          question: question,
          config: config,
          document_ids: selectedDocumentIds.length > 0 ? selectedDocumentIds : undefined,
        }),
      });

      if (!res.ok) {
        throw new Error(`Query failed: ${res.statusText}`);
      }

      const data: ToGQueryResponse = await res.json();
      setResponse(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const getPruningMethodIcon = (method: string) => {
    switch (method) {
      case 'llm': return <Brain className="w-4 h-4" />;
      case 'bm25': return <Zap className="w-4 h-4" />;
      case 'sentence_bert': return <Cpu className="w-4 h-4" />;
      default: return <Network className="w-4 h-4" />;
    }
  };

  const getPruningMethodDescription = (method: string) => {
    switch (method) {
      case 'llm': return 'Highest quality, slower processing';
      case 'bm25': return 'Fast keyword-based scoring';
      case 'sentence_bert': return 'Balanced semantic similarity';
      default: return '';
    }
  };

  return (
    <div className="space-y-6">
      {/* Query Input */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Network className="w-5 h-5" />
            Tree of Graphs Query
          </CardTitle>
          <CardDescription>
            Ask complex questions that require multi-hop reasoning through the knowledge graph
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Label htmlFor="question">Question</Label>
              <Input
                id="question"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="e.g., How is entity A connected to entity B through intermediate entities?"
                disabled={loading}
              />
            </div>

            {/* Document Selection */}
            {completedDocs.length > 0 && (
              <div>
                <Label>Filter by Documents (Optional)</Label>
                <div className="flex flex-wrap gap-2 mt-2">
                  {completedDocs.map((doc) => (
                    <Badge
                      key={doc.id}
                      variant={selectedDocumentIds.includes(doc.id) ? "default" : "outline"}
                      className="cursor-pointer"
                      onClick={() => {
                        setSelectedDocumentIds(prev =>
                          prev.includes(doc.id)
                            ? prev.filter(id => id !== doc.id)
                            : [...prev, doc.id]
                        );
                      }}
                    >
                      {doc.filename}
                    </Badge>
                  ))}
                </div>
                {selectedDocumentIds.length > 0 && (
                  <p className="text-sm text-muted-foreground mt-1">
                    Searching within {selectedDocumentIds.length} selected document(s)
                  </p>
                )}
              </div>
            )}

            <div className="flex gap-2">
              <Button type="submit" disabled={loading}>
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Processing...
                  </>
                ) : (
                  'Submit Query'
                )}
              </Button>

              <Button
                type="button"
                variant="outline"
                onClick={() => setShowConfig(!showConfig)}
              >
                {showConfig ? 'Hide' : 'Show'} Configuration
              </Button>
            </div>

            {/* Configuration Panel */}
            {showConfig && (
              <Card className="mt-4">
                <CardHeader>
                  <CardTitle className="text-sm">ToG Configuration</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>Search Width: {config.search_width}</Label>
                      <Slider
                        value={[config.search_width]}
                        onValueChange={(val) => setConfig({ ...config, search_width: val[0] })}
                        min={1}
                        max={10}
                        step={1}
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        Max entities to explore per depth level
                      </p>
                    </div>

                    <div>
                      <Label>Search Depth: {config.search_depth}</Label>
                      <Slider
                        value={[config.search_depth]}
                        onValueChange={(val) => setConfig({ ...config, search_depth: val[0] })}
                        min={1}
                        max={5}
                        step={1}
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        Max traversal depth (hops)
                      </p>
                    </div>

                    <div>
                      <Label>Pruning Method</Label>
                      <Select
                        value={config.pruning_method}
                        onValueChange={(val: any) => setConfig({ ...config, pruning_method: val })}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="llm">
                            <div className="flex items-center gap-2">
                              <Brain className="w-4 h-4" />
                              LLM (Highest Quality)
                            </div>
                          </SelectItem>
                          <SelectItem value="sentence_bert">
                            <div className="flex items-center gap-2">
                              <Cpu className="w-4 h-4" />
                              SentenceBERT (Balanced)
                            </div>
                          </SelectItem>
                          <SelectItem value="bm25">
                            <div className="flex items-center gap-2">
                              <Zap className="w-4 h-4" />
                              BM25 (Fastest)
                            </div>
                          </SelectItem>
                        </SelectContent>
                      </Select>
                      <p className="text-xs text-muted-foreground mt-1">
                        {getPruningMethodDescription(config.pruning_method)}
                      </p>
                    </div>

                    <div>
                      <Label>Retain Entities: {config.num_retain_entity}</Label>
                      <Slider
                        value={[config.num_retain_entity]}
                        onValueChange={(val) => setConfig({ ...config, num_retain_entity: val[0] })}
                        min={1}
                        max={20}
                        step={1}
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        Max entities to retain during sampling
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id="sufficiency_check"
                      checked={config.enable_sufficiency_check}
                      onChange={(e) => setConfig({ ...config, enable_sufficiency_check: e.target.checked })}
                    />
                    <Label htmlFor="sufficiency_check" className="text-sm">
                      Enable sufficiency checking (early stopping)
                    </Label>
                  </div>
                </CardContent>
              </Card>
            )}
          </form>

          {/* Error Display */}
          {error && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-md text-red-700">
              <strong>Error:</strong> {error}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Results */}
      {response && (
        <Tabs defaultValue="answer" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
        <TabsTrigger value="answer">Answer</TabsTrigger>
        <TabsTrigger value="reasoning">Reasoning Path</TabsTrigger>
        <TabsTrigger value="triplets">Retrieved Triplets</TabsTrigger>
          <TabsTrigger value="visualization">Visualization</TabsTrigger>
          </TabsList>

          <TabsContent value="answer">
          <Card>
          <CardHeader>
          <CardTitle>Answer</CardTitle>
          <div className="flex gap-2 items-center justify-between">
          <div className="flex gap-2 items-center text-sm text-muted-foreground">
          <Badge variant="outline">
              Confidence: {(response.confidence * 100).toFixed(1)}%
            </Badge>
          <Badge variant="outline">
              {response.processing_time_ms}ms
            </Badge>
          <Badge variant="outline" className="flex items-center gap-1">
            {getPruningMethodIcon(config.pruning_method)}
              {config.pruning_method.toUpperCase()}
              </Badge>
              </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => response.query_id && loadVisualization(response.query_id)}
                    disabled={loadingVisualization || !response.query_id}
                  >
                    {loadingVisualization ? (
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <Eye className="w-4 h-4 mr-2" />
                    )}
                    Visualize
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <p className="whitespace-pre-wrap">{response.answer}</p>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="reasoning">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <GitBranch className="w-5 h-5" />
                  Reasoning Path
                </CardTitle>
                <CardDescription>
                  Step-by-step graph exploration process
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {response.reasoning_path.steps?.map((step, idx) => (
                    <div key={idx} className="border-l-2 border-blue-500 pl-4">
                      <div className="flex items-center gap-2 mb-2">
                        <Badge>Depth {step.depth}</Badge>
                        {step.sufficient && (
                          <Badge variant="outline" className="bg-green-50">
                            ✓ Sufficient
                          </Badge>
                        )}
                      </div>

                      <div className="space-y-2 text-sm">
                        <div>
                          <strong>Entities Explored:</strong>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {step.entities_explored?.map((entity, i) => (
                              <Badge key={i} variant="secondary">{entity.name}</Badge>
                            ))}
                          </div>
                        </div>

                        <div>
                          <strong>Relations Selected:</strong>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {step.relations_selected?.map((rel, i) => (
                              <Badge key={i} className="bg-blue-100">{rel.type}</Badge>
                            ))}
                          </div>
                        </div>

                        {step.sufficiency_score !== undefined && (
                          <div>
                            <strong>Sufficiency Score:</strong>{' '}
                            {(step.sufficiency_score * 100).toFixed(1)}%
                          </div>
                        )}

                        {step.reasoning_notes && (
                          <div>
                            <strong>Notes:</strong> {step.reasoning_notes}
                          </div>
                        )}
                      </div>

                      {idx < (response.reasoning_path.steps?.length || 0) - 1 && (
                        <ChevronRight className="w-4 h-4 text-muted-foreground mt-2" />
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="triplets">
            <Card>
              <CardHeader>
                <CardTitle>Retrieved Triplets</CardTitle>
                <CardDescription>
                  Knowledge graph facts used to answer the question
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {response.reasoning_path.retrieved_triplets?.map((triplet, idx) => (
                    <div
                      key={idx}
                      className="flex items-center gap-2 p-3 bg-gray-50 rounded-md text-sm"
                    >
                      <Badge variant="outline">{triplet.subject}</Badge>
                      <span className="text-muted-foreground">→</span>
                      <Badge>{triplet.relation}</Badge>
                      <span className="text-muted-foreground">→</span>
                      <Badge variant="outline">{triplet.object}</Badge>

                      {triplet.confidence !== undefined && (
                        <Badge variant="secondary" className="ml-auto">
                          {(triplet.confidence * 100).toFixed(0)}%
                        </Badge>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

              <TabsContent value="visualization">
                  <Card>
                      <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Network className="w-5 h-5" />
                  Reasoning Path Visualization
                </CardTitle>
                <CardDescription>
                  Interactive graph visualization of the ToG reasoning process
                </CardDescription>
              </CardHeader>
              <CardContent>
                {visualization ? (
                  <div className="bg-gray-50 p-4 rounded-md text-sm">
                    <p className="text-muted-foreground mb-2">Visualization data loaded:</p>
                    <pre className="whitespace-pre-wrap text-xs bg-white p-2 rounded border overflow-auto max-h-96">
                      {JSON.stringify(visualization, null, 2)}
                    </pre>
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    <Network className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>Click "Visualize" to load the reasoning path graph</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      )}
    </div>
  );
}
