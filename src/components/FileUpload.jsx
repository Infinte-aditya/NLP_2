import React, { useState, useCallback } from 'react';

const FileUpload = ({ onFilesSelected }) => {
    const [isDragging, setIsDragging] = useState(false);
    const [uploadedFiles, setUploadedFiles] = useState([]);

    const handleDrag = useCallback((e) => {
        e.preventDefault();
        e.stopPropagation();
    }, []);

    const handleDragIn = useCallback((e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
            setIsDragging(true);
        }
    }, []);

    const handleDragOut = useCallback((e) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);
    }, []);

    const handleDrop = useCallback((e) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);

        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            const files = Array.from(e.dataTransfer.files);
            setUploadedFiles(files);
            onFilesSelected && onFilesSelected(files);
            e.dataTransfer.clearData();
        }
    }, [onFilesSelected]);

    const handleFileInput = (e) => {
        if (e.target.files && e.target.files.length > 0) {
            const files = Array.from(e.target.files);
            setUploadedFiles(files);
            onFilesSelected && onFilesSelected(files);
        }
    };

    return (
        <div
            className={`
                relative border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-all duration-300
                ${isDragging ? 'border-ggs-black bg-gray-50 scale-[1.02]' : 'border-gray-300 hover:border-ggs-darkGrey hover:bg-gray-50/50'}
            `}
            onDragEnter={handleDragIn}
            onDragLeave={handleDragOut}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => document.getElementById('fileInput').click()}
        >
            <input
                type="file"
                id="fileInput"
                className="hidden"
                multiple
                accept=".pdf,.docx,.xml"
                onChange={handleFileInput}
            />

            <div className="flex flex-col items-center gap-4">
                <div className={`p-4 rounded-full bg-gray-100 transition-colors ${isDragging ? 'bg-ggs-black/5' : ''}`}>
                    {/* Simple Upload Icon */}
                    <svg className="w-8 h-8 text-ggs-darkGrey" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                </div>

                <div className="space-y-1">
                    <p className="font-medium text-lg text-ggs-black">
                        {isDragging ? 'Drop files here' : 'Click to upload or drag and drop'}
                    </p>
                    <p className="text-sm text-gray-400">
                        Supported formats: PDF, DOCX, XML
                    </p>
                </div>

                {uploadedFiles.length > 0 && (
                    <div className="card w-full mt-4 bg-white border border-gray-100 rounded-lg p-2 shadow-sm text-left">
                        <div className="text-xs font-semibold uppercase text-gray-400 mb-2 px-2">Selected Files</div>
                        <div className="space-y-2">
                            {uploadedFiles.map((file, idx) => (
                                <div key={idx} className="flex items-center gap-3 p-2 hover:bg-gray-50 rounded">
                                    <div className="w-8 h-8 bg-gray-100 rounded flex items-center justify-center text-xs font-bold text-gray-500">
                                        {file.name.split('.').pop().toUpperCase()}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm font-medium text-ggs-black truncate">{file.name}</p>
                                        <p className="text-xs text-gray-400">{(file.size / 1024).toFixed(1)} KB</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default FileUpload;
