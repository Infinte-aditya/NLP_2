import React, { useState } from 'react';

const DownloadPanel = ({ onReset, downloadUrl, outputFormat = 'PDF', originalFilename, targetLang }) => {
    const [isEvaluating, setIsEvaluating] = useState(false);
    const [evalReport, setEvalReport] = useState(null);
    const [evalError, setEvalError] = useState(null);

    const formatMeta = {
        PDF: { icon: '📄', label: 'Portable Document' },
        XML: { icon: '⚙️', label: 'XML Data' },
        DOCX: { icon: '📝', label: 'Word Document' },
    };
    const meta = formatMeta[outputFormat] || formatMeta['PDF'];
    const formats = [
        { type: outputFormat, icon: meta.icon, label: meta.label, url: downloadUrl },
    ];

    const handleEvaluate = async () => {
        setIsEvaluating(true);
        setEvalReport(null);
        setEvalError(null);
        try {
            const formData = new FormData();
            formData.append('filename', originalFilename);
            formData.append('target_lang', targetLang);

            const res = await fetch('http://localhost:8000/evaluate_result', {
                method: 'POST',
                body: formData
            });
            if (!res.ok) {
                const text = await res.text();
                throw new Error(text || 'Evaluation failed');
            }
            const data = await res.json();
            setEvalReport(data);
        } catch (err) {
            console.error(err);
            setEvalError(err.message || 'Error running evaluation.');
        } finally {
            setIsEvaluating(false);
        }
    };

    return (
        <div className="w-full max-w-2xl mx-auto animate-fade-in-up">
            <div className="bg-white border border-gray-100 rounded-2xl shadow-xl overflow-hidden">
                <div className="bg-ggs-black text-white p-6 text-left">
                    <div className="flex items-center justify-between">
                        <div>
                            <h3 className="text-xl font-bold">Translation Complete</h3>
                            <p className="text-gray-400 text-sm mt-1">Your documents are ready for download.</p>
                        </div>
                        <div className="bg-green-500 rounded-full p-2">
                            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                            </svg>
                        </div>
                    </div>
                </div>

                <div className="p-6">
                    <div className="grid gap-4">
                        {formats.map((fmt) => (
                            <a
                                key={fmt.type}
                                href={fmt.url}
                                target="_blank"
                                rel="noreferrer"
                                className={`flex items-center justify-between p-4 rounded-xl border border-gray-100 hover:border-gray-300 hover:bg-gray-50 transition-all duration-200 group ${!fmt.url || fmt.url === '#' ? 'opacity-50 cursor-not-allowed' : ''}`}
                                onClick={(e) => (!fmt.url || fmt.url === '#') && e.preventDefault()}
                            >
                                <div className="flex items-center gap-4">
                                    <div className="w-12 h-12 bg-gray-100 rounded-lg flex items-center justify-center text-2xl group-hover:scale-110 transition-transform">
                                        {fmt.icon}
                                    </div>
                                    <div className="text-left">
                                        <p className="font-bold text-ggs-black">Download as {fmt.type}</p>
                                        <p className="text-xs text-gray-500">{fmt.label}</p>
                                    </div>
                                </div>
                                <div className="text-ggs-black opacity-0 group-hover:opacity-100 transition-opacity -translate-x-2 group-hover:translate-x-0 transform duration-200">
                                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                    </svg>
                                </div>
                            </a>
                        ))}
                    </div>

                    {/* Evaluation Section */}
                    {originalFilename && (
                        <div className="mt-6 p-4 bg-gray-50 border border-gray-100 rounded-xl transition-all">
                            {!evalReport && !isEvaluating && (
                                <button
                                    onClick={handleEvaluate}
                                    className="w-full flex items-center justify-center gap-2 py-3 px-4 bg-white border border-gray-200 shadow-sm rounded-lg font-medium text-gray-700 hover:text-blue-600 hover:border-blue-300 transition-colors"
                                >
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>
                                    Evaluate Translation Quality
                                </button>
                            )}

                            {isEvaluating && (
                                <div className="flex items-center justify-center py-4 text-gray-500 gap-2">
                                    <svg className="w-5 h-5 animate-spin text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                                    Running automated document analysis...
                                </div>
                            )}

                            {evalError && (
                                <div className="text-red-500 text-sm mt-2">{evalError}</div>
                            )}

                            {evalReport && (
                                <div className="space-y-4 animate-fade-in text-left">
                                    <h4 className="font-bold text-gray-800 border-b pb-2">Evaluation Results</h4>

                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="bg-white p-4 rounded-lg border border-gray-100 shadow-sm flex flex-col justify-center">
                                            <div className="text-sm text-gray-500 font-medium">English Word Leakage</div>
                                            <div className="text-2xl font-bold flex items-end gap-1 mt-1">
                                                <span className={evalReport.english_leakage.leakage_percent < 5 ? 'text-green-500' : (evalReport.english_leakage.leakage_percent < 10 ? 'text-yellow-500' : 'text-red-500')}>
                                                    {evalReport.english_leakage.leakage_percent}%
                                                </span>
                                            </div>
                                            <div className="text-xs text-gray-400 mt-1 whitespace-pre-wrap">Targeting 0% (Lower is better)<br />Leaked words: {evalReport.english_leakage.english_word_count}</div>
                                        </div>

                                        <div className="bg-white p-4 rounded-lg border border-gray-100 shadow-sm flex flex-col justify-center">
                                            <div className="text-sm text-gray-500 font-medium">Glossary Coverage</div>
                                            <div className="text-2xl font-bold flex items-end gap-1 mt-1">
                                                <span className={evalReport.glossary_coverage.coverage_percent === 100 ? 'text-green-500' : (evalReport.glossary_coverage.coverage_percent > 80 ? 'text-yellow-500' : 'text-red-500')}>
                                                    {evalReport.glossary_coverage.coverage_percent}%
                                                </span>
                                            </div>
                                            <div className="text-xs text-gray-400 mt-1">
                                                Targeting 100% (Higher is better)<br />
                                                Missed terms: {evalReport.glossary_coverage.terms_missed.length > 0 ? evalReport.glossary_coverage.terms_missed.join(', ') : 'None'}
                                            </div>
                                        </div>
                                    </div>

                                </div>
                            )}
                        </div>
                    )}

                    <div className="mt-8 text-center">
                        <button
                            onClick={onReset}
                            className="text-sm text-gray-400 hover:text-ggs-black underline transition-colors"
                        >
                            Translate more documents
                        </button>
                    </div>
                </div>
            </div>

            <style>{`
                @keyframes fadeInUp {
                    from { opacity: 0; transform: translateY(20px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                .animate-fade-in-up {
                    animation: fadeInUp 0.5s ease-out forwards;
                }
            `}</style>
        </div>
    );
};

export default DownloadPanel;
