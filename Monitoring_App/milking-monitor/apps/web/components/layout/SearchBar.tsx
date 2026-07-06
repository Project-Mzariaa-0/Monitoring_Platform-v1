'use client';

import React, { useState, useRef, useEffect } from 'react';
import styles from './SearchBar.module.css';

interface SearchBarProps {
  placeholder?: string;
  onSearch?: (query: string) => void;
  suggestions?: string[];
  onSuggestionSelect?: (suggestion: string) => void;
}

export function SearchBar({
  placeholder = 'Search...',
  onSearch,
  suggestions = [],
  onSuggestionSelect,
}: SearchBarProps) {
  const [value, setValue] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const suggestionsRef = useRef<HTMLDivElement>(null);

  const filteredSuggestions = suggestions.filter(
    (s) => s.toLowerCase().includes(value.toLowerCase()) && value.length > 0
  );

  const showSuggestions = isFocused && filteredSuggestions.length > 0;

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!showSuggestions) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex((prev) =>
          prev < filteredSuggestions.length - 1 ? prev + 1 : prev
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex((prev) => (prev > 0 ? prev - 1 : -1));
        break;
      case 'Enter':
        e.preventDefault();
        if (selectedIndex >= 0) {
          selectSuggestion(filteredSuggestions[selectedIndex]);
        } else {
          handleSearch();
        }
        break;
      case 'Escape':
        setIsFocused(false);
        break;
    }
  };

  const handleSearch = () => {
    if (onSearch && value.trim()) {
      onSearch(value);
      setIsFocused(false);
    }
  };

  const selectSuggestion = (suggestion: string) => {
    setValue(suggestion);
    setIsFocused(false);
    onSuggestionSelect?.(suggestion);
  };

  return (
    <div className={styles.searchContainer}>
      <div className={`${styles.searchWrapper} ${isFocused ? styles.focused : ''}`}>
        <input
          ref={inputRef}
          type="text"
          className={styles.searchInput}
          placeholder={placeholder}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => {
            setTimeout(() => setIsFocused(false), 200);
          }}
          onKeyDown={handleKeyDown}
          aria-label="Search"
          aria-autocomplete="list"
        />
        <button
          className={styles.searchButton}
          onClick={handleSearch}
          aria-label="Search"
        >
          🔍
        </button>
      </div>
      {showSuggestions && (
        <div ref={suggestionsRef} className={styles.suggestions}>
          {filteredSuggestions.map((suggestion, index) => (
            <button
              key={suggestion}
              className={`${styles.suggestionItem} ${
                index === selectedIndex ? styles.selected : ''
              }`}
              onClick={() => selectSuggestion(suggestion)}
            >
              {suggestion}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
