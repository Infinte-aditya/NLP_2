import React from 'react';

const languages = [
    'Hindi', 'Tamil', 'Telugu', 'Malayalam', 'Kannada'
];

const LanguageSelector = ({ selectedLanguages, onChange }) => {
    const toggleLanguage = (lang) => {
        if (selectedLanguages.includes(lang)) {
            onChange(selectedLanguages.filter(l => l !== lang));
        } else {
            onChange([...selectedLanguages, lang]);
        }
    };

    return (
        <div className="text-left w-full max-w-2xl mx-auto">
            <label className="block text-sm font-medium text-gray-500 mb-3 uppercase tracking-wide">Target Languages</label>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {languages.map((lang) => {
                    const isSelected = selectedLanguages.includes(lang);
                    return (
                        <div
                            key={lang}
                            onClick={() => toggleLanguage(lang)}
                            className={`
                                group relative flex items-center p-3 rounded-lg cursor-pointer border transition-all duration-200
                                ${isSelected
                                    ? 'border-ggs-black bg-ggs-black text-white ring-2 ring-offset-2 ring-ggs-black'
                                    : 'border-gray-300 bg-white text-gray-700 hover:border-gray-500 hover:bg-gray-50'
                                }
                            `}
                        >
                            <div className={`
                                w-5 h-5 rounded border mr-3 flex items-center justify-center transition-colors
                                ${isSelected ? 'border-white bg-white' : 'border-gray-300 group-hover:border-gray-400'}
                            `}>
                                {isSelected && (
                                    <svg className="w-3 h-3 text-ggs-black" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M5 13l4 4L19 7" />
                                    </svg>
                                )}
                            </div>
                            <span className="font-medium select-none">{lang}</span>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default LanguageSelector;
