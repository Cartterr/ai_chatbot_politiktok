import React from 'react';

const TestComponent = () => {
  return (
    <div className="p-6 max-w-sm mx-auto bg-white rounded-xl shadow-lg flex items-center space-x-4 mt-4">
      <div className="shrink-0">
        <div className="h-12 w-12 bg-indigo-500 rounded-full flex items-center justify-center text-white text-xl font-bold">
          T
        </div>
      </div>
      <div>
        <div className="text-xl font-medium text-black">Tailwind Test</div>
        <p className="text-gray-500">If you see this styled nicely, Tailwind is working!</p>
      </div>
    </div>
  );
};

export default TestComponent;