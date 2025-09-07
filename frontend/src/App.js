import React, { useState, useEffect } from "react";
import "./App.css";
import axios from "axios";
import { Button } from "./components/ui/button";
import { Textarea } from "./components/ui/textarea";
import { Input } from "./components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./components/ui/card";
import { Badge } from "./components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./components/ui/tabs";
import { Upload, FileText, Clock, CheckSquare, Target, Sparkles, Bot, Users, TrendingUp } from "lucide-react";
import { toast } from "sonner";
import { Toaster } from "./components/ui/sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [meetingTitle, setMeetingTitle] = useState("");
  const [meetingContent, setMeetingContent] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [summary, setSummary] = useState(null);
  const [meetings, setMeetings] = useState([]);
  const [activeTab, setActiveTab] = useState("summarize");

  useEffect(() => {
    fetchMeetings();
  }, []);

  const fetchMeetings = async () => {
    try {
      const response = await axios.get(`${API}/meetings`);
      setMeetings(response.data);
    } catch (error) {
      console.error("Error fetching meetings:", error);
    }
  };

  const handleTextSummary = async () => {
    if (!meetingTitle.trim() || !meetingContent.trim()) {
      toast.error("Please provide both title and content");
      return;
    }

    setIsLoading(true);
    try {
      const response = await axios.post(`${API}/summarize-text`, {
        title: meetingTitle,
        content: meetingContent
      });
      
      setSummary(response.data);
      setActiveTab("results");
      toast.success("Meeting summarized successfully!");
      
      // Clear form
      setMeetingTitle("");
      setMeetingContent("");
      
      // Refresh meetings list
      fetchMeetings();
    } catch (error) {
      console.error("Error summarizing meeting:", error);
      toast.error("Failed to summarize meeting. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileSummary = async () => {
    if (!meetingTitle.trim() || !selectedFile) {
      toast.error("Please provide both title and file");
      return;
    }

    setIsLoading(true);
    try {
      const formData = new FormData();
      formData.append("title", meetingTitle);
      formData.append("file", selectedFile);

      const response = await axios.post(`${API}/summarize-file`, formData, {
        headers: {
          "Content-Type": "multipart/form-data"
        }
      });
      
      setSummary(response.data);
      setActiveTab("results");
      toast.success("File processed and summarized successfully!");
      
      // Clear form
      setMeetingTitle("");
      setSelectedFile(null);
      
      // Refresh meetings list
      fetchMeetings();
    } catch (error) {
      console.error("Error processing file:", error);
      toast.error("Failed to process file. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (!file.name.endsWith('.txt') && !file.name.endsWith('.docx')) {
        toast.error("Please select a .txt or .docx file");
        return;
      }
      setSelectedFile(file);
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-xl flex items-center justify-center">
                <Bot className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-gray-900 to-gray-600 bg-clip-text text-transparent">
                  MeetSum AI
                </h1>
                <p className="text-sm text-gray-500">AI-Powered Meeting Summarizer</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <Badge variant="secondary" className="flex items-center space-x-1">
                <Sparkles className="w-3 h-3" />
                <span>GPT-4 Powered</span>
              </Badge>
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      {activeTab === "summarize" && !summary && (
        <section className="py-12 px-4 sm:px-6 lg:px-8">
          <div className="max-w-4xl mx-auto text-center">
            <div className="inline-flex items-center space-x-2 bg-blue-100 text-blue-800 px-4 py-2 rounded-full text-sm font-medium mb-6">
              <Sparkles className="w-4 h-4" />
              <span>Transform meetings into actionable insights</span>
            </div>
            
            <h2 className="text-4xl sm:text-5xl font-bold text-gray-900 mb-6 leading-tight">
              Turn Your Meetings Into
              <span className="bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent block">
                Actionable Intelligence
              </span>
            </h2>
            
            <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto leading-relaxed">
              Upload your meeting transcripts or paste content to get AI-powered summaries, 
              extract action items, and identify key decisions automatically.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-12">
              <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
                <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center mb-4">
                  <FileText className="w-6 h-6 text-blue-600" />
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">Smart Summarization</h3>
                <p className="text-gray-600 text-sm">Get concise, comprehensive summaries of your meetings</p>
              </div>
              
              <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
                <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center mb-4">
                  <CheckSquare className="w-6 h-6 text-green-600" />
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">Action Items</h3>
                <p className="text-gray-600 text-sm">Automatically extract tasks and assignments</p>
              </div>
              
              <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
                <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center mb-4">
                  <Target className="w-6 h-6 text-purple-600" />
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">Key Insights</h3>
                <p className="text-gray-600 text-sm">Identify important decisions and discussion points</p>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pb-12">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-3 mb-8">
            <TabsTrigger value="summarize" className="flex items-center space-x-2">
              <Bot className="w-4 h-4" />
              <span>Summarize</span>
            </TabsTrigger>
            <TabsTrigger value="results" className="flex items-center space-x-2">
              <TrendingUp className="w-4 h-4" />
              <span>Results</span>
            </TabsTrigger>
            <TabsTrigger value="history" className="flex items-center space-x-2">
              <Clock className="w-4 h-4" />
              <span>History</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="summarize" className="space-y-8">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Text Input */}
              <Card className="shadow-sm border-0 bg-white/60 backdrop-blur-sm">
                <CardHeader className="pb-4">
                  <CardTitle className="flex items-center space-x-2">
                    <FileText className="w-5 h-5 text-blue-600" />
                    <span>Text Input</span>
                  </CardTitle>
                  <CardDescription>
                    Paste your meeting transcript or notes directly
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <Input
                    placeholder="Meeting title (e.g., Weekly Team Sync - Jan 15)"
                    value={meetingTitle}
                    onChange={(e) => setMeetingTitle(e.target.value)}
                    className="border-gray-200 focus:border-blue-500"
                  />
                  <Textarea
                    placeholder="Paste your meeting content here..."
                    value={meetingContent}
                    onChange={(e) => setMeetingContent(e.target.value)}
                    rows={12}
                    className="border-gray-200 focus:border-blue-500 resize-none"
                  />
                  <Button 
                    onClick={handleTextSummary}
                    disabled={isLoading || !meetingTitle.trim() || !meetingContent.trim()}
                    className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-medium py-2.5"
                  >
                    {isLoading ? (
                      <div className="flex items-center space-x-2">
                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                        <span>Processing...</span>
                      </div>
                    ) : (
                      <div className="flex items-center space-x-2">
                        <Sparkles className="w-4 h-4" />
                        <span>Summarize Text</span>
                      </div>
                    )}
                  </Button>
                </CardContent>
              </Card>

              {/* File Upload */}
              <Card className="shadow-sm border-0 bg-white/60 backdrop-blur-sm">
                <CardHeader className="pb-4">
                  <CardTitle className="flex items-center space-x-2">
                    <Upload className="w-5 h-5 text-green-600" />
                    <span>File Upload</span>
                  </CardTitle>
                  <CardDescription>
                    Upload your meeting document (.txt or .docx)
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <Input
                    placeholder="Meeting title (e.g., Board Meeting - Q4 Review)"
                    value={meetingTitle}
                    onChange={(e) => setMeetingTitle(e.target.value)}
                    className="border-gray-200 focus:border-green-500"
                  />
                  
                  <div className="border-2 border-dashed border-gray-200 rounded-lg p-8 text-center hover:border-green-300 transition-colors">
                    <Upload className="w-8 h-8 text-gray-400 mx-auto mb-4" />
                    <div className="space-y-2">
                      <p className="text-sm font-medium text-gray-700">
                        {selectedFile ? selectedFile.name : "Choose a file to upload"}
                      </p>
                      <p className="text-xs text-gray-500">
                        Supports .txt and .docx files
                      </p>
                    </div>
                    <input
                      type="file"
                      accept=".txt,.docx"
                      onChange={handleFileChange}
                      className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                    />
                  </div>
                  
                  <Button 
                    onClick={handleFileSummary}
                    disabled={isLoading || !meetingTitle.trim() || !selectedFile}
                    className="w-full bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white font-medium py-2.5"
                  >
                    {isLoading ? (
                      <div className="flex items-center space-x-2">
                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                        <span>Processing...</span>
                      </div>
                    ) : (
                      <div className="flex items-center space-x-2">
                        <Upload className="w-4 h-4" />
                        <span>Process File</span>
                      </div>
                    )}
                  </Button>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="results">
            {summary ? (
              <div className="space-y-6">
                <Card className="shadow-sm border-0 bg-white/80 backdrop-blur-sm">
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div>
                        <CardTitle className="text-2xl text-gray-900">{summary.title}</CardTitle>
                        <CardDescription className="flex items-center space-x-2 mt-1">
                          <Clock className="w-4 h-4" />
                          <span>{formatDate(summary.created_at)}</span>
                        </CardDescription>
                      </div>
                      <Badge className="bg-green-100 text-green-800 border-green-200">
                        <CheckSquare className="w-3 h-3 mr-1" />
                        Processed
                      </Badge>
                    </div>
                  </CardHeader>
                </Card>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  {/* Summary */}
                  <Card className="lg:col-span-2 shadow-sm border-0 bg-white/80 backdrop-blur-sm">
                    <CardHeader>
                      <CardTitle className="flex items-center space-x-2">
                        <FileText className="w-5 h-5 text-blue-600" />
                        <span>Summary</span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">{summary.summary}</p>
                    </CardContent>
                  </Card>

                  {/* Key Points */}
                  <Card className="shadow-sm border-0 bg-white/80 backdrop-blur-sm">
                    <CardHeader>
                      <CardTitle className="flex items-center space-x-2">
                        <Target className="w-5 h-5 text-purple-600" />
                        <span>Key Points</span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <ul className="space-y-2">
                        {summary.key_points.map((point, index) => (
                          <li key={index} className="flex items-start space-x-2">
                            <div className="w-1.5 h-1.5 bg-purple-500 rounded-full mt-2 flex-shrink-0"></div>
                            <span className="text-sm text-gray-700">{point}</span>
                          </li>
                        ))}
                      </ul>
                    </CardContent>
                  </Card>
                </div>

                {/* Action Items */}
                <Card className="shadow-sm border-0 bg-white/80 backdrop-blur-sm">
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-2">
                      <CheckSquare className="w-5 h-5 text-green-600" />
                      <span>Action Items</span>
                      <Badge variant="secondary">{summary.action_items.length}</Badge>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {summary.action_items.map((item, index) => (
                        <div key={index} className="bg-green-50 border border-green-200 rounded-lg p-4">
                          <div className="flex items-start space-x-3">
                            <div className="w-6 h-6 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                              <span className="text-xs font-medium text-green-700">{index + 1}</span>
                            </div>
                            <p className="text-sm text-gray-700 leading-relaxed">{item}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>
            ) : (
              <div className="text-center py-12">
                <Bot className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">No Results Yet</h3>
                <p className="text-gray-500">Process a meeting to see the AI-generated summary and action items.</p>
                <Button 
                  onClick={() => setActiveTab("summarize")}
                  className="mt-4 bg-blue-600 hover:bg-blue-700"
                >
                  Start Summarizing
                </Button>
              </div>
            )}
          </TabsContent>

          <TabsContent value="history">
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold text-gray-900">Meeting History</h2>
                <Badge variant="secondary">{meetings.length} meetings</Badge>
              </div>

              {meetings.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {meetings.map((meeting) => (
                    <Card key={meeting.id} className="shadow-sm border-0 bg-white/80 backdrop-blur-sm hover:shadow-md transition-shadow cursor-pointer"
                          onClick={() => {
                            setSummary(meeting);
                            setActiveTab("results");
                          }}>
                      <CardHeader className="pb-3">
                        <CardTitle className="text-lg line-clamp-2">{meeting.title}</CardTitle>
                        <CardDescription className="flex items-center space-x-2">
                          <Clock className="w-4 h-4" />
                          <span>{formatDate(meeting.created_at)}</span>
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        <p className="text-sm text-gray-600 line-clamp-3 mb-3">
                          {meeting.summary}
                        </p>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-4 text-xs text-gray-500">
                            <span className="flex items-center space-x-1">
                              <CheckSquare className="w-3 h-3" />
                              <span>{meeting.action_items.length} actions</span>
                            </span>
                            <span className="flex items-center space-x-1">
                              <Target className="w-3 h-3" />
                              <span>{meeting.key_points.length} points</span>
                            </span>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12">
                  <Users className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">No Meetings Yet</h3>
                  <p className="text-gray-500">Your meeting summaries will appear here once you start processing them.</p>
                  <Button 
                    onClick={() => setActiveTab("summarize")}
                    className="mt-4 bg-blue-600 hover:bg-blue-700"
                  >
                    Summarize Your First Meeting
                  </Button>
                </div>
              )}
            </div>
          </TabsContent>
        </Tabs>
      </main>
      <Toaster />
    </div>
  );
}

export default App;