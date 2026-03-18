import React, { useState, useRef } from 'react';

const EvaluationPanel = () => {
    const [referenceFile, setReferenceFile] = useState(null);
    const [translatedFile, setTranslatedFile] = useState(null);
    const [isEvaluating, setIsEvaluating] = useState(false);
    const [results, setResults] = useState(null);
    const [error, setError] = useState(null);

    const refInputRef = useRef(null);
    const transInputRef = useRef(null);

    const handleEvaluate = async () => {
        if (!referenceFile || !translatedFile) return;

        setIsEvaluating(true);
        setResults(null);
        setError(null);

        try {
            const formData = new FormData();
            formData.append('reference_file', referenceFile);
            formData.append('translated_file', translatedFile);

            const res = await fetch('http://localhost:8000/evaluate_xml', {
                method: 'POST',
                body: formData,
            });

            if (!res.ok) {
                const text = await res.text();
                throw new Error(text || 'Evaluation failed');
            }

            const data = await res.json();
            setResults(data);
        } catch (err) {
            console.error(err);
            setError(err.message || 'Error running evaluation.');
        } finally {
            setIsEvaluating(false);
        }
    };

    const handleReset = () => {
        setReferenceFile(null);
        setTranslatedFile(null);
        setResults(null);
        setError(null);
        if (refInputRef.current) refInputRef.current.value = '';
        if (transInputRef.current) transInputRef.current.value = '';
    };

    const FileDropZone = ({ label, description, file, onFileChange, inputRef, id }) => (
        <div
            className={`
                relative border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all duration-300
                ${file ? 'border-green-400 bg-green-50/50' : 'border-gray-300 hover:border-gray-500 hover:bg-gray-50/50'}
            `}
            onClick={() => inputRef.current?.click()}
        >
            <input
                type="file"
                id={id}
                ref={inputRef}
                className="hidden"
                accept=".xml"
                onChange={(e) => {
                    if (e.target.files && e.target.files.length > 0) {
                        onFileChange(e.target.files[0]);
                    }
                }}
            />
            <div className="flex flex-col items-center gap-2">
                {file ? (
                    <>
                        <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
                            <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                            </svg>
                        </div>
                        <p className="text-sm font-medium text-green-700 truncate max-w-full">{file.name}</p>
                        <p className="text-xs text-gray-400">{(file.size / 1024).toFixed(1)} KB</p>
                    </>
                ) : (
                    <>
                        <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center">
                            <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                            </svg>
                        </div>
                        <p className="text-sm font-medium text-gray-700">{label}</p>
                        <p className="text-xs text-gray-400">{description}</p>
                    </>
                )}
            </div>
        </div>
    );

    const ScoreCard = ({ label, value, description, colorFn }) => {
        const displayValue = typeof value === 'number' ? value.toFixed(4) : value;
        const color = colorFn ? colorFn(value) : 'text-gray-900';
        return (
            <div className="bg-white p-5 rounded-xl border border-gray-100 shadow-sm flex flex-col justify-center">
                <div className="text-xs uppercase tracking-wider text-gray-400 font-semibold">{label}</div>
                <div className={`text-3xl font-bold mt-2 ${color}`}>{displayValue}</div>
                <div className="text-xs text-gray-400 mt-1">{description}</div>
            </div>
        );
    };

    return (
        <div className="w-full max-w-4xl mx-auto">
            {/* Section Header */}
            <div className="flex items-center gap-3 mb-6">
                <div className="h-px flex-1 bg-gray-200" />
                <div className="flex items-center gap-2 text-gray-500">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                    </svg>
                    <span className="text-sm font-semibold uppercase tracking-wider">Evaluate Translation Quality</span>
                </div>
                <div className="h-px flex-1 bg-gray-200" />
            </div>

            <div className="bg-white border border-gray-100 rounded-2xl shadow-lg overflow-hidden">
                <div className="p-6">
                    <p className="text-gray-500 text-sm mb-6 text-center">
                        Upload a <strong>reference XML</strong> and a <strong>translated XML</strong> to compute quality scores.
                        <br />
                        <span className="text-xs text-gray-400">@@-marked transliterated words are automatically handled during scoring.</span>
                    </p>

                    {/* File Upload Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                        <FileDropZone
                            label="Reference XML"
                            description="Human / gold-standard translation"
                            file={referenceFile}
                            onFileChange={setReferenceFile}
                            inputRef={refInputRef}
                            id="refFileInput"
                        />
                        <FileDropZone
                            label="Translated XML"
                            description="Machine-translated output"
                            file={translatedFile}
                            onFileChange={setTranslatedFile}
                            inputRef={transInputRef}
                            id="transFileInput"
                        />
                    </div>

                    {/* Evaluate Button */}
                    {!results && (
                        <button
                            onClick={handleEvaluate}
                            disabled={!referenceFile || !translatedFile || isEvaluating}
                            className={`
                                w-full py-3 px-6 rounded-xl font-semibold text-sm uppercase tracking-wider transition-all duration-300
                                ${referenceFile && translatedFile && !isEvaluating
                                    ? 'bg-ggs-black text-white hover:bg-gray-800 shadow-md hover:shadow-lg cursor-pointer'
                                    : 'bg-gray-200 text-gray-400 cursor-not-allowed'}
                            `}
                        >
                            {isEvaluating ? (
                                <span className="flex items-center justify-center gap-2">
                                    <svg className="w-4 h-4 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                    </svg>
                                    Evaluating...
                                </span>
                            ) : (
                                'Evaluate'
                            )}
                        </button>
                    )}

                    {/* Error */}
                    {error && (
                        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">
                            {error}
                        </div>
                    )}

                    {/* Results */}
                    {results && (
                        <div className="mt-2 animate-fade-in">
                            <div className="flex items-center justify-between mb-4">
                                <h4 className="font-bold text-gray-800 text-sm uppercase tracking-wider">Evaluation Scores</h4>
                                <span className="text-xs text-gray-400">
                                    Ref: {results.reference_segments} segs · Trans: {results.translated_segments} segs
                                </span>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-1 gap-4">
                                <ScoreCard
                                    label="Semantic Meaning"
                                    value={results.diagnostics?.avg_segment_semantic}
                                    description="0–100, AI meaning match"
                                    colorFn={(v) => v >= 75 ? 'text-green-600' : v >= 50 ? 'text-yellow-600' : 'text-red-500'}
                                />
                            </div>

                            {/* ── Diagnostics Section ──────────────────────── */}
                            {results.diagnostics && (
                                <div className="mt-6 space-y-5">
                                    {/* Quality Distribution */}
                                    <div className="bg-gray-50 rounded-xl p-5 border border-gray-100">
                                        <h5 className="text-xs font-bold uppercase tracking-wider text-gray-500 mb-3">
                                            Segment Quality Distribution
                                        </h5>
                                        <p className="text-xs text-gray-400 mb-3">
                                            {results.diagnostics.segment_count_compared} segments compared · Average Semantic Score: <span className="font-bold text-gray-700">{results.diagnostics.avg_segment_semantic}%</span>
                                        </p>
                                        {/* Distribution Bar */}
                                        <div className="flex rounded-lg overflow-hidden h-6 mb-2">
                                            {results.diagnostics.quality_distribution.good_pct > 0 && (
                                                <div
                                                    className="bg-green-500 flex items-center justify-center text-white text-[10px] font-bold"
                                                    style={{ width: `${results.diagnostics.quality_distribution.good_pct}%` }}
                                                >
                                                    {results.diagnostics.quality_distribution.good_pct > 8 ? `${results.diagnostics.quality_distribution.good_pct}%` : ''}
                                                </div>
                                            )}
                                            {results.diagnostics.quality_distribution.fair_pct > 0 && (
                                                <div
                                                    className="bg-yellow-400 flex items-center justify-center text-gray-800 text-[10px] font-bold"
                                                    style={{ width: `${results.diagnostics.quality_distribution.fair_pct}%` }}
                                                >
                                                    {results.diagnostics.quality_distribution.fair_pct > 8 ? `${results.diagnostics.quality_distribution.fair_pct}%` : ''}
                                                </div>
                                            )}
                                            {results.diagnostics.quality_distribution.poor_pct > 0 && (
                                                <div
                                                    className="bg-red-400 flex items-center justify-center text-white text-[10px] font-bold"
                                                    style={{ width: `${results.diagnostics.quality_distribution.poor_pct}%` }}
                                                >
                                                    {results.diagnostics.quality_distribution.poor_pct > 8 ? `${results.diagnostics.quality_distribution.poor_pct}%` : ''}
                                                </div>
                                            )}
                                        </div>
                                        <div className="flex gap-4 text-xs text-gray-500">
                                            <span className="flex items-center gap-1">
                                                <span className="w-2.5 h-2.5 rounded-full bg-green-500 inline-block"></span>
                                                Good ({results.diagnostics.quality_distribution.good} segs, Semantic ≥ 75)
                                            </span>
                                            <span className="flex items-center gap-1">
                                                <span className="w-2.5 h-2.5 rounded-full bg-yellow-400 inline-block"></span>
                                                Fair ({results.diagnostics.quality_distribution.fair} segs, 40-75)
                                            </span>
                                            <span className="flex items-center gap-1">
                                                <span className="w-2.5 h-2.5 rounded-full bg-red-400 inline-block"></span>
                                                Poor ({results.diagnostics.quality_distribution.poor} segs, &lt;40)
                                            </span>
                                        </div>
                                    </div>

                                    {/* Recommendations */}
                                    {results.diagnostics.recommendations?.length > 0 && (
                                        <div className="bg-gray-50 rounded-xl p-5 border border-gray-100">
                                            <h5 className="text-xs font-bold uppercase tracking-wider text-gray-500 mb-3">
                                                Issues &amp; Recommendations
                                            </h5>
                                            <div className="space-y-2.5">
                                                {results.diagnostics.recommendations.map((rec, idx) => (
                                                    <div
                                                        key={idx}
                                                        className={`p-3 rounded-lg border-l-4 ${rec.severity === 'high'
                                                            ? 'border-red-400 bg-red-50'
                                                            : rec.severity === 'medium'
                                                                ? 'border-yellow-400 bg-yellow-50'
                                                                : 'border-green-400 bg-green-50'
                                                            }`}
                                                    >
                                                        <div className="flex items-center gap-2 mb-1">
                                                            <span className={`text-xs font-bold uppercase ${rec.severity === 'high' ? 'text-red-600'
                                                                : rec.severity === 'medium' ? 'text-yellow-700'
                                                                    : 'text-green-600'
                                                                }`}>
                                                                {rec.severity === 'high' ? '⚠' : rec.severity === 'medium' ? '◐' : '✓'} {rec.title}
                                                            </span>
                                                        </div>
                                                        <p className="text-xs text-gray-600 leading-relaxed">
                                                            {rec.detail}
                                                        </p>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* Worst Segments */}
                                    {results.diagnostics.worst_segments?.length > 0 && (
                                        <details className="bg-gray-50 rounded-xl border border-gray-100">
                                            <summary className="p-5 cursor-pointer text-xs font-bold uppercase tracking-wider text-gray-500 hover:text-gray-700">
                                                Lowest Scoring Segments (click to expand)
                                            </summary>
                                            <div className="px-5 pb-5 space-y-3">
                                                {results.diagnostics.worst_segments.map((seg, idx) => (
                                                    <div key={idx} className="bg-white rounded-lg p-3 border border-gray-100 text-xs">
                                                        <div className="flex items-center justify-between mb-2">
                                                            <span className="text-gray-400 font-medium">Segment #{seg.index + 1}</span>
                                                            <span className={`font-bold ${seg.semantic >= 75 ? 'text-green-600' : seg.semantic >= 40 ? 'text-yellow-600' : 'text-red-500'
                                                                }`}>
                                                                Semantic: {seg.semantic}%
                                                            </span>
                                                        </div>
                                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                                                            <div>
                                                                <span className="text-[10px] text-gray-400 uppercase font-semibold">Reference</span>
                                                                <p className="text-gray-700 mt-0.5 leading-relaxed break-all">{seg.ref_preview}</p>
                                                            </div>
                                                            <div>
                                                                <span className="text-[10px] text-gray-400 uppercase font-semibold">Translation</span>
                                                                <p className="text-gray-700 mt-0.5 leading-relaxed break-all">{seg.trans_preview}</p>
                                                            </div>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </details>
                                    )}

                                    {/* Best Segments */}
                                    {results.diagnostics.best_segments?.length > 0 && (
                                        <details className="bg-gray-50 rounded-xl border border-gray-100">
                                            <summary className="p-5 cursor-pointer text-xs font-bold uppercase tracking-wider text-gray-500 hover:text-gray-700">
                                                Highest Scoring Segments (click to expand)
                                            </summary>
                                            <div className="px-5 pb-5 space-y-3">
                                                {results.diagnostics.best_segments.map((seg, idx) => (
                                                    <div key={idx} className="bg-white rounded-lg p-3 border border-green-100 text-xs">
                                                        <div className="flex items-center justify-between mb-2">
                                                            <span className="text-gray-400 font-medium">Segment #{seg.index + 1}</span>
                                                            <span className="font-bold text-green-600">
                                                                Semantic: {seg.semantic}%
                                                            </span>
                                                        </div>
                                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                                                            <div>
                                                                <span className="text-[10px] text-gray-400 uppercase font-semibold">Reference</span>
                                                                <p className="text-gray-700 mt-0.5 leading-relaxed break-all">{seg.ref_preview}</p>
                                                            </div>
                                                            <div>
                                                                <span className="text-[10px] text-gray-400 uppercase font-semibold">Translation</span>
                                                                <p className="text-gray-700 mt-0.5 leading-relaxed break-all">{seg.trans_preview}</p>
                                                            </div>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </details>
                                    )}
                                </div>
                            )}

                            <button
                                onClick={handleReset}
                                className="mt-5 w-full text-sm text-gray-400 hover:text-ggs-black underline transition-colors"
                            >
                                Evaluate another pair
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default EvaluationPanel;
