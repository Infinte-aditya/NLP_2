import React, { useState } from 'react';
import IntroAnimation from './components/IntroAnimation';
import FileUpload from './components/FileUpload';
import LanguageSelector from './components/LanguageSelector';
import TranslateButton from './components/TranslateButton';
import DownloadPanel from './components/DownloadPanel';
import EvaluationPanel from './components/EvaluationPanel';

function App() {
  const [showMainUI, setShowMainUI] = useState(false);
  const [files, setFiles] = useState([]);
  const [selectedLanguages, setSelectedLanguages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isTranslated, setIsTranslated] = useState(false);

  const [progress, setProgress] = useState({ status: 'Idle', percent: 0 });

  const [downloadUrl, setDownloadUrl] = useState(null);

  const handleIntroComplete = () => {
    setShowMainUI(true);
  };

  const handleTranslate = async () => {
    if (files.length === 0 || selectedLanguages.length === 0) return;

    setIsLoading(true);
    setProgress({ status: 'Starting...', percent: 0 });

    // Start Polling
    const pollInterval = setInterval(async () => {
      try {
        const res = await fetch('http://localhost:8000/progress');
        const data = await res.json();
        setProgress(data);
      } catch (e) {
        console.error("Polling error", e);
      }
    }, 500);

    try {
      const formData = new FormData();
      formData.append('file', files[0]);
      // Detect output format from file extension
      const fileName = files[0].name.toLowerCase();
      const isXml = fileName.endsWith('.xml');
      const outputFormat = isXml ? 'xml' : 'pdf';
      // Use the first selected language
      formData.append('target_lang', selectedLanguages[0]);
      formData.append('output_format', outputFormat);

      const response = await fetch('http://localhost:8000/translate', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Translation failed');
      }

      const data = await response.json();
      setDownloadUrl(`http://localhost:8000${data.download_url}`);
      setIsTranslated(true);
      setProgress({ status: 'Completed', percent: 100 });
    } catch (error) {
      console.error("Error:", error);
      alert("Translation failed. Please checking if backend is running.");
    } finally {
      clearInterval(pollInterval);
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setFiles([]);
    setSelectedLanguages([]);
    setIsTranslated(false);
  };

  return (
    <div className="min-h-screen bg-white text-ggs-black font-sans selection:bg-ggs-black selection:text-white">
      {/* Intro Overlay */}
      {!showMainUI && <IntroAnimation onComplete={handleIntroComplete} />}

      {/* Main Content */}
      <div className={`transition-all duration-500 ${showMainUI ? 'block' : 'hidden'}`}>
        {/* Header */}
        <header className="fixed top-0 left-0 right-0 h-16 bg-white/80 backdrop-blur-md border-b border-gray-100 flex items-center px-6 md:px-12 z-40 transition-all duration-500">
          <div className={`flex items-center gap-2 transition-transform duration-1000 ${showMainUI ? 'translate-y-0' : '-translate-y-10'}`}>
            <span className="text-2xl font-bold tracking-tighter">GGS</span>
            <span className="text-sm text-gray-500 uppercase tracking-widest border-l border-gray-300 pl-2">Information Services</span>
          </div>
        </header>

        {/* Main Layout */}
        <main className="pt-24 px-6 md:px-12 max-w-7xl mx-auto pb-12 w-full">
          <div className="flex flex-col gap-12 text-center max-w-4xl mx-auto mt-8 md:mt-12">
            <div className="space-y-4">
              <h1 className="text-4xl md:text-5xl font-light tracking-tight text-ggs-black">
                Automotive Document Translation
              </h1>
              <p className="text-gray-500 text-lg">
                Securely translate technical documents with industrial precision.
              </p>
            </div>

            {/* Logic: Show Input sections if not translated, else show DownloadPanel */}
            {!isTranslated ? (
              <div className="space-y-12 animate-fade-in">
                {/* File Upload Section */}
                <section>
                  <FileUpload onFilesSelected={setFiles} />
                </section>

                {/* Language Selector */}
                <section>
                  <LanguageSelector
                    selectedLanguages={selectedLanguages}
                    onChange={setSelectedLanguages}
                  />
                </section>

                {/* Action Button */}
                <section>
                  <TranslateButton
                    onClick={handleTranslate}
                    disabled={files.length === 0 || selectedLanguages.length === 0}
                    isLoading={isLoading}
                    progress={progress}
                  />
                </section>

                {/* Evaluation Section */}
                <section className="mt-8">
                  <EvaluationPanel />
                </section>
              </div>
            ) : (
              <DownloadPanel
                onReset={handleReset}
                downloadUrl={downloadUrl}
                outputFormat={files.length > 0 && files[0].name.toLowerCase().endsWith('.xml') ? 'XML' : 'PDF'}
                originalFilename={files.length > 0 ? files[0].name : ''}
                targetLang={selectedLanguages.length > 0 ? selectedLanguages[0] : ''}
              />
            )}
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;
