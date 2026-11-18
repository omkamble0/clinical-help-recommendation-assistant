"use client";

import React, { useState, useEffect, useRef, useMemo } from "react";
import { UserMode, SearchResponse } from "@/lib/types";
import { searchClinicalRAG, searchClinicalTaxonomy, fetchTaxonomyStats, TaxonomyEntity } from "@/lib/api";
import { ClinicianView } from "@/components/clinician-view";
import { PatientView } from "@/components/patient-view";
import { CitationDrawer } from "@/components/citation-drawer";
import { TriageBanner } from "@/components/triage-banner";
import { getMatchingSuggestions, SearchSuggestion } from "@/lib/suggestions";
import { QueryValidationComponent } from "@/components/QueryValidationComponent";
import {
  Search,
  Stethoscope,
  HeartHandshake,
  ShieldCheck,
  Sparkles,
  RefreshCw,
  X,
  ChevronRight,
  HeartPulse,
  ArrowLeft,
  BookOpen,
  ArrowRight,
  Columns3,
  CheckCircle2,
  Lock,
  ExternalLink,
  Activity
} from "lucide-react";
import { IntegratedChatThread } from "@/components/integrated-chat-thread";
import { MedicalWikiViewer } from "@/components/medical-wiki-viewer";

export default function Home() {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<UserMode>("patient");
  const [compareMode, setCompareMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [activeCitation, setActiveCitation] = useState<number | null>(null);

  const [result, setResult] = useState<SearchResponse | null>(null);
  const [patientResult, setPatientResult] = useState<SearchResponse | null>(null);

  // Primary Workspace View: 'assistant' | 'wiki' | 'split'
  const [primaryView, setPrimaryView] = useState<"assistant" | "wiki" | "split">("assistant");
  const [selectedWikiTopicId, setSelectedWikiTopicId] = useState<string>("DOC-CARD-001");

  // Autocomplete state
  const [isFocused, setIsFocused] = useState(false);
  const [filteredSuggestions, setFilteredSuggestions] = useState<SearchSuggestion[]>([]);
  const [selectedIndex, setSelectedIndex] = useState<number>(-1);
  const [taxonomyResults, setTaxonomyResults] = useState<TaxonomyEntity[]>([]);
  const [taxonomyStats, setTaxonomyStats] = useState<{ total_conditions: number; cms_icd10_count: number; who_icd11_count: number } | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const hasTopic = Boolean(result || patientResult || loading);

  // First-time user friendly guidance & animated curiosity placeholder
  const [showGuideBar, setShowGuideBar] = useState(true);
  const [animatedPlaceholder, setAnimatedPlaceholder] = useState("");
  const [activePathway, setActivePathway] = useState<"symptoms" | "meds" | "conditions">("symptoms");
  const [previewTab, setPreviewTab] = useState<"patient" | "clinician">("patient");

  const pathwayConfigs = {
    symptoms: {
      icon: "🩺",
      title: "1. Check Symptoms",
      description: "Feeling unwell or worried? Describe what hurts to see safe next steps.",
      placeholder: "Describe your symptoms (e.g. sharp chest tightness when breathing deeply)...",
      chips: [
        "Crushing chest pressure radiating to left arm",
        "Dizzy and lightheaded when standing up quickly",
        "Persistent dry hacking cough for 3 weeks"
      ]
    },
    meds: {
      icon: "💊",
      title: "2. Pill & Drug Safety",
      description: "Check side effects, missed doses, and whether two medicines mix safely.",
      placeholder: "Enter medicine names (e.g. Can I take Metformin with Ibuprofen?)...",
      chips: [
        "Can I take paracetamol with blood pressure pills?",
        "Paxlovid drug interactions with cholesterol statins",
        "Semaglutide side effects and what to do if I miss a dose"
      ]
    },
    conditions: {
      icon: "📋",
      title: "3. Understand Conditions & Labs",
      description: "Ask about a diagnosis or typed lab numbers (HbA1c, BP, eGFR) in simple words.",
      placeholder: "Enter a condition or lab test (e.g. What does HbA1c 8.2% and eGFR 45 mean?)...",
      chips: [
        "What does high microalbuminuria in urine mean?",
        "How to reverse prediabetes HbA1c of 6.1%",
        "Explaining Stage 2 high blood pressure guidelines"
      ]
    }
  };

  const patientPrompts = useMemo(() => [
    "Why do my hands feel cold even when it's warm?",
    "Can I take paracetamol with blood pressure pills?",
    "Why am I getting headaches every afternoon?",
    "What should I ask my doctor about prediabetes?",
    "Is it normal to feel dizzy right after standing up?"
  ], []);

  const clinicianPrompts = useMemo(() => [
    "First-line medication options for Stage 2 hypertension with albuminuria",
    "SGLT2 inhibitor and GLP-1 receptor agonist cardiorenal trial endpoints",
    "Paxlovid CYP3A4 drug interactions and renal cutoffs (eGFR <30)",
    "GINA guidelines on SMART regimen for mild-to-moderate asthma"
  ], []);

  // Smooth rotating placeholder that pauses on full question
  useEffect(() => {
    if (query.trim().length > 0) {
      setAnimatedPlaceholder("");
      return;
    }

    const prompts = mode === "patient" ? patientPrompts : clinicianPrompts;
    let promptIdx = 0;
    let charIdx = 0;
    let isDeleting = false;
    let timeoutId: ReturnType<typeof setTimeout>;

    const tick = () => {
      const current = prompts[promptIdx % prompts.length];
      if (!isDeleting) {
        setAnimatedPlaceholder(current.substring(0, charIdx + 1));
        charIdx++;
        if (charIdx === current.length) {
          isDeleting = true;
          timeoutId = setTimeout(tick, 2500);
          return;
        }
      } else {
        setAnimatedPlaceholder(current.substring(0, charIdx - 1));
        charIdx--;
        if (charIdx === 0) {
          isDeleting = false;
          promptIdx++;
          timeoutId = setTimeout(tick, 500);
          return;
        }
      }
      timeoutId = setTimeout(tick, isDeleting ? 20 : 40);
    };

    timeoutId = setTimeout(tick, 150);
    return () => clearTimeout(timeoutId);
  }, [mode, query, patientPrompts, clinicianPrompts]);

  // Fetch taxonomy stats on mount
  useEffect(() => {
    fetchTaxonomyStats()
      .then((data) => setTaxonomyStats(data))
      .catch((err) => console.debug("Taxonomy stats notice:", err));
  }, []);

  // Update suggestions when query changes
  useEffect(() => {
    const list = getMatchingSuggestions(query, 5);
    setFilteredSuggestions(list);
    setSelectedIndex(-1);

    if (query.trim().length >= 2) {
      const timer = setTimeout(() => {
        searchClinicalTaxonomy(query.trim(), undefined, 3)
          .then((res) => setTaxonomyResults(res.results || []))
          .catch(() => setTaxonomyResults([]));
      }, 120);
      return () => clearTimeout(timer);
    } else {
      setTaxonomyResults([]);
    }
  }, [query]);

  // Click outside to close autocomplete
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(event.target as Node)
      ) {
        setIsFocused(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Curated prominent queries for instant demonstration
  const featuredQueries = [
    {
      title: "Hypertension Guidelines",
      subtitle: "First-line therapies with renal protection (microalbuminuria)",
      query: "What are the first-line medication options for stage 2 hypertension with microalbuminuria?",
      tag: "ACC/AHA",
      icon: "💊"
    },
    {
      title: "Chest Pain Triage",
      subtitle: "Crushing substernal pressure with left arm radiation",
      query: "I have severe crushing substernal chest pain, cold sweats, and difficulty breathing",
      tag: "Emergency Check",
      icon: "🚨"
    },
    {
      title: "Diabetes & GLP-1/SGLT2i",
      subtitle: "Cardiorenal risk reduction and titration schedule",
      query: "Semaglutide cardiovascular outcomes and titration schedule in Type 2 Diabetes",
      tag: "ADA 2024",
      icon: "🩸"
    },
    {
      title: "Asthma Controller Therapy",
      subtitle: "GINA guidelines on SMART regimen for mild-to-moderate asthma",
      query: "What is the recommended inhaler approach for mild to moderate asthma?",
      tag: "GINA",
      icon: "🫁"
    }
  ];

  const handleOpenWikiTopic = (topicIdOrName: string) => {
    setSelectedWikiTopicId(topicIdOrName);
    setPrimaryView("wiki");
    setIsFocused(false);
  };

  const handleSearch = async (overrideQuery?: string, targetMode?: UserMode) => {
    const q = overrideQuery || query;
    if (!q.trim()) return;

    setPrimaryView("assistant");
    setIsFocused(false);
    setLoading(true);
    setActiveCitation(null);

    const currentMode = targetMode || mode;

    if (compareMode) {
      const [proRes, patRes] = await Promise.all([
        searchClinicalRAG(q, "professional"),
        searchClinicalRAG(q, "patient"),
      ]);
      setResult(proRes);
      setPatientResult(patRes);
    } else {
      const res = await searchClinicalRAG(q, currentMode);
      setResult(res);
      setPatientResult(null);
    }

    setLoading(false);
  };

  const handleSelectSuggestion = (sug: SearchSuggestion) => {
    setQuery(sug.query);
    setIsFocused(false);
    handleSearch(sug.query);
  };

  const handleClearTopic = () => {
    setResult(null);
    setPatientResult(null);
    setQuery("");
    setIsFocused(false);
    setActiveCitation(null);
    setPrimaryView("assistant");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!isFocused || filteredSuggestions.length === 0) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev < filteredSuggestions.length - 1 ? prev + 1 : 0));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev > 0 ? prev - 1 : filteredSuggestions.length - 1));
    } else if (e.key === "Enter") {
      if (selectedIndex >= 0 && selectedIndex < filteredSuggestions.length) {
        e.preventDefault();
        handleSelectSuggestion(filteredSuggestions[selectedIndex]);
      }
    } else if (e.key === "Escape") {
      setIsFocused(false);
    }
  };

  const handleSelectCitation = (index: number) => {
    setActiveCitation(index);
    const element = document.getElementById(`source-${index}`);
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  };

  const activeQueryText = result?.query || patientResult?.query || query;

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900 font-sans selection:bg-indigo-100 selection:text-indigo-900">
      {/* ================= REFINED TOP NAVBAR ================= */}
      <header className="sticky top-0 z-40 bg-white/80 backdrop-blur-md border-b border-slate-200/70">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
          {/* Brand Logo */}
          <div
            onClick={handleClearTopic}
            className="flex items-center gap-2.5 cursor-pointer select-none group"
          >
            <div className="w-9 h-9 rounded-xl bg-slate-900 text-white flex items-center justify-center shadow-xs group-hover:bg-indigo-600 transition-colors">
              <HeartPulse className="w-5 h-5 text-indigo-400 group-hover:text-white transition-colors" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-base font-extrabold tracking-tight text-slate-900">AegisMed</span>
                <span className="text-[10px] font-bold tracking-wider uppercase px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
                  Clinical AI
                </span>
              </div>
            </div>
          </div>

          {/* Center Navigation Tabs */}
          <nav className="hidden md:flex items-center gap-1 p-1 bg-slate-100/80 rounded-xl border border-slate-200/60">
            <button
              type="button"
              onClick={() => setPrimaryView("assistant")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                primaryView === "assistant"
                  ? "bg-white text-slate-900 shadow-xs font-bold"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
              <span>AI Assistant</span>
            </button>

            <button
              type="button"
              onClick={() => setPrimaryView("wiki")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                primaryView === "wiki"
                  ? "bg-white text-slate-900 shadow-xs font-bold"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <BookOpen className="w-3.5 h-3.5 text-slate-500" />
              <span>Medical Library</span>
              <span className="text-[10px] px-1 rounded bg-slate-200/80 text-slate-700">600</span>
            </button>
          </nav>

          {/* Right Mode Toggle & Cloud Telemetry */}
          <div className="flex items-center gap-2.5">
            {/* Live Cloud Status Pill */}
            <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-emerald-50/90 border border-emerald-200/80 text-[11px] font-semibold text-emerald-800 shadow-2xs">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              <span>AWS Bedrock • Redis 0.2ms</span>
            </div>

            <div className="flex items-center p-1 bg-slate-100 rounded-xl border border-slate-200/80">
              <button
                type="button"
                onClick={() => {
                  setCompareMode(false);
                  setMode("patient");
                  if (result) handleSearch(query, "patient");
                }}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                  !compareMode && mode === "patient"
                    ? "bg-white text-indigo-700 shadow-2xs font-bold"
                    : "text-slate-500 hover:text-slate-900"
                }`}
              >
                <HeartHandshake className="w-3.5 h-3.5" />
                <span>Patient</span>
              </button>
              <button
                type="button"
                onClick={() => {
                  setCompareMode(false);
                  setMode("professional");
                  if (result) handleSearch(query, "professional");
                }}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                  !compareMode && mode === "professional"
                    ? "bg-white text-teal-700 shadow-2xs font-bold"
                    : "text-slate-500 hover:text-slate-900"
                }`}
              >
                <Stethoscope className="w-3.5 h-3.5" />
                <span>Clinician</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* ================= LANDING HERO (Balanced 2-Column Desktop Grid) ================= */}
      {!hasTopic && primaryView === "assistant" ? (
        <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 sm:pt-12 pb-16 animate-fade-in">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            {/* Left Column: Intent, Search, Examples (lg:col-span-7) */}
            <div className="lg:col-span-7 space-y-6 text-left">
              {/* Welcoming Badge */}
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-200/80 text-indigo-700 text-xs font-semibold shadow-2xs">
                <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                <span>Health guidance made simple</span>
              </div>

              {/* Simple, Humble Headline */}
              <div className="space-y-2.5">
                <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-slate-900 tracking-tight leading-tight">
                  Everyday health questions, <br className="hidden sm:inline" />
                  <span className="bg-gradient-to-r from-indigo-600 via-blue-600 to-teal-600 bg-clip-text text-transparent">
                    explained clearly.
                  </span>
                </h1>

                <p className="text-slate-600 text-sm sm:text-base leading-relaxed max-w-xl">
                  Simple, reliable information on symptoms, everyday medicines, and lab tests — helping you understand your health and prepare for conversations with your doctor.
                </p>
              </div>

              {/* 3 Intent Pathways (Solves "What is this website for?") */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-left">
                {(["symptoms", "meds", "conditions"] as const).map((key) => {
                  const cfg = pathwayConfigs[key];
                  const isSelected = activePathway === key;
                  return (
                    <button
                      key={key}
                      type="button"
                      onClick={() => {
                        setActivePathway(key);
                        inputRef.current?.focus();
                      }}
                      className={`p-3.5 rounded-2xl border text-left transition-all cursor-pointer ${
                        isSelected
                          ? "bg-white border-2 border-indigo-600 shadow-sm scale-[1.01]"
                          : "bg-white/80 border-slate-200/90 shadow-2xs hover:border-slate-300 hover:bg-white"
                      }`}
                    >
                      <div className="text-2xl mb-1.5">{cfg.icon}</div>
                      <div className="font-bold text-slate-900 text-xs sm:text-sm">{cfg.title}</div>
                      <p className="text-[11px] text-slate-500 mt-1 leading-snug line-clamp-2">
                        {cfg.description}
                      </p>
                    </button>
                  );
                })}
              </div>

              {/* Active Conversational Input Box */}
              <div className="bg-white rounded-3xl p-3 sm:p-4 border border-slate-200/90 shadow-md shadow-slate-100/60 space-y-3 text-left">
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    handleSearch();
                  }}
                  className="relative flex items-center w-full h-14 sm:h-16 bg-slate-50 rounded-2xl border border-slate-200 focus-within:border-indigo-600 focus-within:bg-white focus-within:ring-4 focus-within:ring-indigo-50 transition-all p-1.5"
                >
                  <div className="pl-3 pr-2 text-xl select-none">
                    {pathwayConfigs[activePathway].icon}
                  </div>

                  <input
                    ref={inputRef}
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onFocus={() => setIsFocused(true)}
                    onKeyDown={handleKeyDown}
                    placeholder={pathwayConfigs[activePathway].placeholder}
                    className="w-full h-full pl-2 pr-28 sm:pr-36 bg-transparent text-slate-900 placeholder:text-slate-400 text-xs sm:text-sm outline-none"
                  />

                  <div className="absolute right-2 flex items-center gap-1.5">
                    {query && (
                      <button
                        type="button"
                        onClick={() => {
                          setQuery("");
                          inputRef.current?.focus();
                        }}
                        className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg transition-colors"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    )}

                    <button
                      type="submit"
                      disabled={loading || !query.trim()}
                      className="px-4 sm:px-5 py-2.5 h-10 sm:h-11 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs sm:text-sm tracking-wide transition-all shadow-xs disabled:opacity-40 flex items-center gap-1.5 shrink-0"
                    >
                      {loading ? (
                        <RefreshCw className="w-4 h-4 animate-spin" />
                      ) : (
                        <>
                          <span>Check</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </>
                      )}
                    </button>
                  </div>
                </form>

                {/* Quick 1-Click Prompt Chips */}
                <div className="flex flex-wrap items-center gap-1.5 pt-0.5 px-1">
                  <span className="text-[11px] font-semibold text-slate-400 mr-1">Tap an example:</span>
                  {pathwayConfigs[activePathway].chips.map((chipText, cIdx) => (
                    <button
                      key={cIdx}
                      type="button"
                      onClick={() => {
                        setQuery(chipText);
                        handleSearch(chipText);
                      }}
                      className="px-2.5 py-1 text-xs rounded-lg bg-slate-100 hover:bg-indigo-50 hover:text-indigo-700 text-slate-600 border border-slate-200 transition-colors text-left cursor-pointer"
                    >
                      {chipText}
                    </button>
                  ))}
                </div>

                {/* Autocomplete Dropdown */}
                {isFocused && (filteredSuggestions.length > 0 || taxonomyResults.length > 0) && (
                  <div
                    ref={dropdownRef}
                    className="bg-white border border-slate-200 rounded-xl shadow-lg text-left overflow-hidden divide-y divide-slate-100 mt-2"
                  >
                    <div className="p-2 max-h-56 overflow-y-auto">
                      {filteredSuggestions.map((sug, idx) => (
                        <div
                          key={sug.id}
                          onClick={() => handleSelectSuggestion(sug)}
                          className={`px-3 py-2 rounded-lg cursor-pointer transition-colors flex items-center justify-between gap-3 ${
                            selectedIndex === idx ? "bg-indigo-50" : "hover:bg-slate-50"
                          }`}
                        >
                          <div className="min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-bold text-slate-900 truncate">
                                {sug.label}
                              </span>
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">
                                {sug.healthBody}
                              </span>
                            </div>
                            <p className="text-[11px] text-slate-500 truncate mt-0.5">
                              {sug.description}
                            </p>
                          </div>
                          <ChevronRight className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="pt-1">
                  <QueryValidationComponent
                    query={query}
                    compact={true}
                    onApplyCorrection={(corrected) => {
                      setQuery(corrected);
                      handleSearch(corrected);
                    }}
                  />
                </div>
              </div>

              {/* Minimalist Trust Badges */}
              <div className="flex flex-wrap items-center gap-4 sm:gap-6 pt-1 text-xs text-slate-500">
                <span className="flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-emerald-600" />
                  <span>Grounded in clinical guidelines</span>
                </span>
                <span className="flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 text-indigo-600" />
                  <span>Clear, everyday language</span>
                </span>
                <span className="flex items-center gap-1.5">
                  <Lock className="w-4 h-4 text-slate-500" />
                  <span>Private & anonymous to use</span>
                </span>
              </div>
            </div>

            {/* Right Column: Interactive Live Preview & Popular Topics (lg:col-span-5) */}
            <div className="lg:col-span-5 space-y-4 pt-1">
              {/* "See How We Answer" Live Preview Card */}
              <div className="bg-gradient-to-br from-indigo-50/70 via-white to-blue-50/70 rounded-3xl p-4 sm:p-5 border border-indigo-100 shadow-xs space-y-3 text-left">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-bold uppercase tracking-wider bg-indigo-600 text-white px-2 py-0.5 rounded-md">
                      Live Preview
                    </span>
                    <span className="text-xs font-bold text-slate-800">
                      How AegisMed answers questions
                    </span>
                  </div>

                  <div className="flex items-center gap-1 bg-white p-0.5 rounded-lg border border-indigo-100 text-[11px]">
                    <button
                      type="button"
                      onClick={() => setPreviewTab("patient")}
                      className={`px-2.5 py-0.5 rounded-md font-bold transition-all ${
                        previewTab === "patient"
                          ? "bg-indigo-100 text-indigo-800"
                          : "text-slate-500 hover:text-slate-900"
                      }`}
                    >
                      Patient Summary
                    </button>
                    <button
                      type="button"
                      onClick={() => setPreviewTab("clinician")}
                      className={`px-2.5 py-0.5 rounded-md font-bold transition-all ${
                        previewTab === "clinician"
                          ? "bg-indigo-100 text-indigo-800"
                          : "text-slate-500 hover:text-slate-900"
                      }`}
                    >
                      Clinical Evidence
                    </button>
                  </div>
                </div>

                {/* Sample Question Bar */}
                <div className="bg-white/90 p-2.5 rounded-xl border border-indigo-100 text-xs text-slate-700 flex items-center gap-2 shadow-2xs">
                  <span className="font-bold text-indigo-700 shrink-0">Example:</span>
                  <span className="italic text-slate-600 truncate">&ldquo;Can I take Paracetamol with Lisinopril for high blood pressure?&rdquo;</span>
                </div>

                {/* Preview Answer Box */}
                {previewTab === "patient" ? (
                  <div className="bg-white p-4 rounded-2xl border border-slate-200/90 shadow-2xs space-y-2.5 animate-fade-in">
                    <div className="flex items-center justify-between">
                      <span className="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200">
                        <span>✓</span> Generally Safe with Monitoring
                      </span>
                      <span className="text-[10px] text-slate-500">Everyday plain English</span>
                    </div>
                    <p className="text-xs text-slate-600 leading-relaxed">
                      <strong>Direct Answer:</strong> Yes, Paracetamol is typically the safest everyday pain reliever when taking blood pressure medicine like Lisinopril. Unlike Ibuprofen or Naproxen (NSAIDs), it will not interfere with blood pressure control or stress kidneys.
                    </p>
                    <div className="bg-slate-50 rounded-xl p-2.5 border border-slate-100 text-[11px] text-slate-600 space-y-1">
                      <div className="font-bold text-slate-700 flex items-center gap-1">
                        <span>💬</span> 2 Questions to ask your doctor or pharmacist:
                      </div>
                      <ul className="list-disc list-inside text-slate-500 space-y-0.5">
                        <li>&ldquo;What is my safe maximum daily limit of paracetamol?&rdquo;</li>
                        <li>&ldquo;Are any of my other daily pills already combined with acetaminophen?&rdquo;</li>
                      </ul>
                    </div>
                  </div>
                ) : (
                  <div className="bg-white p-4 rounded-2xl border border-slate-200/90 shadow-2xs space-y-2.5 animate-fade-in">
                    <div className="flex items-center justify-between">
                      <span className="inline-flex items-center gap-1.5 text-xs font-bold text-indigo-700 bg-indigo-50 px-2.5 py-1 rounded-full border border-indigo-200">
                        <span>🩺</span> Oxford CEBM Level 1 Evidence
                      </span>
                      <span className="text-[10px] text-slate-500 font-mono">DDI Sweep &bull; Renal cutoffs</span>
                    </div>
                    <p className="text-xs text-slate-600 leading-relaxed font-mono text-[11px]">
                      <strong>Therapeutic Consensus:</strong> Acetaminophen is preferred over NSAIDs (such as ibuprofen or naproxen) in patients receiving ACEi/ARB therapy. NSAIDs inhibit renal prostaglandin synthesis, blunting the antihypertensive efficacy of Lisinopril and elevating AKI / hyperkalemia risk (ACC/AHA 2024 Guidelines, Section 7.4).
                    </p>
                    <div className="text-[10px] text-slate-400 font-mono border-t border-slate-100 pt-1.5 flex items-center justify-between">
                      <span>Guideline: ACC/AHA Hypertension &bull; FDA DDI Registry</span>
                      <span>Dosage Ceiling: 3,000 mg/day max</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Popular Topics in Library Card */}
              <div className="bg-white rounded-2xl p-4 border border-slate-200/80 shadow-2xs space-y-2.5 text-left">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-800">Popular Topics in Library</span>
                  <button
                    type="button"
                    onClick={() => setPrimaryView("wiki")}
                    className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1 transition-colors"
                  >
                    <span>Browse 600 guidelines</span>
                    <ArrowRight className="w-3 h-3" />
                  </button>
                </div>
                <div className="divide-y divide-slate-100">
                  <button
                    type="button"
                    onClick={() => {
                      setQuery("Essential Hypertension");
                      handleSearch("Essential Hypertension");
                    }}
                    className="w-full py-2 flex items-center justify-between text-left hover:text-indigo-600 group transition-colors cursor-pointer"
                  >
                    <div>
                      <div className="text-xs font-semibold text-slate-800 group-hover:text-indigo-600">Essential High Blood Pressure</div>
                      <div className="text-[11px] text-slate-500">Blood pressure stages and everyday lifestyle guidance</div>
                    </div>
                    <ChevronRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-indigo-600 shrink-0" />
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setQuery("Type 2 Diabetes Mellitus");
                      handleSearch("Type 2 Diabetes Mellitus");
                    }}
                    className="w-full py-2 flex items-center justify-between text-left hover:text-indigo-600 group transition-colors cursor-pointer"
                  >
                    <div>
                      <div className="text-xs font-semibold text-slate-800 group-hover:text-indigo-600">Type 2 Diabetes &amp; HbA1c</div>
                      <div className="text-[11px] text-slate-500">Understanding blood sugar tests and target ranges</div>
                    </div>
                    <ChevronRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-indigo-600 shrink-0" />
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setQuery("Mild to Moderate Asthma");
                      handleSearch("Mild to Moderate Asthma");
                    }}
                    className="w-full py-2 flex items-center justify-between text-left hover:text-indigo-600 group transition-colors cursor-pointer"
                  >
                    <div>
                      <div className="text-xs font-semibold text-slate-800 group-hover:text-indigo-600">Asthma Action Guidance</div>
                      <div className="text-[11px] text-slate-500">Inhaler techniques and daily symptom tracking</div>
                    </div>
                    <ChevronRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-indigo-600 shrink-0" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </section>
      ) : null}

      {/* ================= COMPACT REFINED TOPIC BAR (When Result is Active) ================= */}
      {hasTopic && primaryView === "assistant" && (
        <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6 pb-2 animate-fade-in">
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pb-4 border-b border-slate-200/80 mb-6">
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={handleClearTopic}
                className="p-2 rounded-xl bg-white border border-slate-200 text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors shadow-2xs"
                title="Back to Home"
              >
                <ArrowLeft className="w-4 h-4" />
              </button>
              <div>
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                  {mode === "professional" ? "Clinician Protocol" : "Patient Guide"}
                </span>
                <h2 className="text-xl font-bold text-slate-900 leading-tight">
                  {activeQueryText}
                </h2>
              </div>
            </div>

            {/* Quick Toggle Mode on Result Screen */}
            <div className="flex items-center gap-2 self-start sm:self-center">
              <div className="flex items-center p-1 bg-slate-100 rounded-xl border border-slate-200">
                <button
                  type="button"
                  onClick={() => {
                    setCompareMode(false);
                    setMode("patient");
                    handleSearch(activeQueryText, "patient");
                  }}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                    !compareMode && mode === "patient" ? "bg-white text-indigo-700 shadow-2xs font-bold" : "text-slate-500"
                  }`}
                >
                  Patient View
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setCompareMode(false);
                    setMode("professional");
                    handleSearch(activeQueryText, "professional");
                  }}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                    !compareMode && mode === "professional" ? "bg-white text-teal-700 shadow-2xs font-bold" : "text-slate-500"
                  }`}
                >
                  Clinician View
                </button>
              </div>

              <button
                type="button"
                onClick={() => setCompareMode(!compareMode)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all ${
                  compareMode
                    ? "bg-purple-600 text-white border-purple-600 shadow-xs"
                    : "bg-white text-slate-700 border-slate-200 hover:bg-slate-50"
                }`}
                title="Compare Patient and Clinician side-by-side"
              >
                <Columns3 className="w-3.5 h-3.5" />
                <span>Compare</span>
              </button>
            </div>
          </div>
        </section>
      )}

      {/* ================= RESULTS / WIKI / SPLIT WORKSPACE ================= */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {primaryView === "wiki" ? (
          <div className="py-6 animate-fade-in">
            <MedicalWikiViewer
              initialTopicId={selectedWikiTopicId}
              mode={mode === "professional" ? "clinician" : "patient"}
              onModeChange={(newMode) => setMode(newMode === "clinician" ? "professional" : "patient")}
              embedded={true}
              onSelectQueryForAssistant={(q) => {
                setQuery(q);
                setPrimaryView("assistant");
                handleSearch(q);
              }}
            />
          </div>
        ) : primaryView === "split" ? (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start py-6 animate-fade-in">
            <div className="lg:col-span-7 h-[85vh]">
              <MedicalWikiViewer
                initialTopicId={selectedWikiTopicId}
                mode={mode === "professional" ? "clinician" : "patient"}
                onModeChange={(newMode) => setMode(newMode === "clinician" ? "professional" : "patient")}
                embedded={true}
                onSelectQueryForAssistant={(q) => {
                  setQuery(q);
                  handleSearch(q);
                }}
              />
            </div>
            <div className="lg:col-span-5 h-[85vh] bg-white border border-slate-200 rounded-2xl shadow-xs p-4 flex flex-col overflow-hidden">
              <IntegratedChatThread
                initialTopic={query || selectedWikiTopicId}
                mode={mode}
                response={result}
                activeCitation={activeCitation}
                onSelectCitation={handleSelectCitation}
              />
            </div>
          </div>
        ) : loading ? (
          /* Sleek Loading State */
          <div className="p-12 bg-white border border-slate-200/80 rounded-2xl text-center shadow-xs animate-fade-in space-y-4 max-w-lg mx-auto my-12">
            <div className="w-12 h-12 rounded-xl bg-indigo-50 flex items-center justify-center mx-auto text-indigo-600">
              <RefreshCw className="w-5 h-5 animate-spin" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">
                Synthesizing Evidence & Safety Guardrails...
              </h3>
              <p className="text-xs text-slate-500 mt-1">
                Cross-referencing Oxford CEBM guidelines with deterministic clinical safety rules.
              </p>
            </div>
          </div>
        ) : compareMode && result && patientResult ? (
          /* Dual Perspective Compare View */
          <div className="space-y-6 pb-16">
            {result?.triage_alert && (
              <div className="max-w-4xl mx-auto">
                <TriageBanner alert={result.triage_alert} />
              </div>
            )}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <PatientView
                response={patientResult}
                activeCitation={activeCitation}
                onSelectCitation={handleSelectCitation}
              />
              <ClinicianView
                response={result}
                activeCitation={activeCitation}
                onSelectCitation={handleSelectCitation}
              />
            </div>
            <div className="mt-8">
              <CitationDrawer
                sources={result.sources}
                activeCitation={activeCitation}
                onSelectCitation={handleSelectCitation}
              />
            </div>
          </div>
        ) : result ? (
          /* Single Perspective + Evidence Drawer Layout */
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start pb-16">
            <div className="lg:col-span-8 space-y-6">
              {result?.triage_alert && <TriageBanner alert={result.triage_alert} />}

              {mode === "professional" ? (
                <ClinicianView
                  response={result}
                  activeCitation={activeCitation}
                  onSelectCitation={handleSelectCitation}
                />
              ) : (
                <PatientView
                  response={result}
                  activeCitation={activeCitation}
                  onSelectCitation={handleSelectCitation}
                />
              )}

              <IntegratedChatThread
                initialTopic={activeQueryText}
                mode={mode}
                response={result}
                activeCitation={activeCitation}
                onSelectCitation={handleSelectCitation}
              />
            </div>

            {/* Evidence Sidebar */}
            <div className="lg:col-span-4 sticky top-24">
              <CitationDrawer
                sources={result.sources}
                activeCitation={activeCitation}
                onSelectCitation={handleSelectCitation}
              />
            </div>
          </div>
        ) : null}
      </main>

      {/* ================= REFINED FOOTER ================= */}
      <footer className="border-t border-slate-200/80 mt-20 py-8 bg-white/50 text-center text-xs text-slate-400">
        <p className="max-w-xl mx-auto leading-relaxed">
          AegisMed is an evidence-based clinical decision support tool grounded in peer-reviewed medical literature. Not a substitute for formal in-person clinical diagnosis.
        </p>
      </footer>
    </div>
  );
}
