function mat2wav(mask, scale, idx)
%MAT2WAV  - save audio track from array-of-structs MAT variable to WAV format file
%
%	usage:  mat2wav(mask, scale, idx)
%
% Use this procedure to save the audio track from an MVIEW-compatible array-of-structs
% variable stored in a MAT file to a separate MS WAVE format file with the same name.
%
% All files matching string MASK are converted (may also be specified as an explicit 
% cellstr list of files for processing)
%
% Audio is scaled to optional +/- SCALE range (default 1).
%
% Optional IDX (into MAT variable) defaults to 1; if two indices are specified
% output is to a stereo file
%
% Example:  convert files matching JW11* with a +/-2048 (12 bit) range
% >> mat2wav('JW11*',2048)

% mkt 07/06
% mkt 05/16 updated

if nargin < 1,
	eval('help mat2wav');
	return;
end;
if nargin<2 || isempty(scale), scale = 1; end;
if nargin<3 || isempty(idx), idx = 1; end;

if iscell(mask),		% explicit list
	fl = mask;
	p = fileparts(fl{1});
else,					% build list
	fl = dir(mask);
	fl = {fl.name}';
	for k = 1 : length(fl),
		[p,f,e] = fileparts(fl{k});
		fl{k} = f;
	end;
	p = fileparts(mask);
end;

for k = 1 : length(fl),
	try,
		data = load(fullfile(p,fl{k}),fl{k});
		data = data.(fl{k});
	catch,
		error('unable to load array-of-structs data from %s.mat', fullfile(p,fl{k}));
	end;
	if length(idx) > 1 && data(idx(1)).SRATE>5000 && data(idx(2)).SRATE>5000 
		s = [data(idx(1)).SIGNAL ./ scale , data(idx(2)).SIGNAL ./ scale];
	else,
		s = data(idx(1)).SIGNAL ./ scale;
	end;
	fn = fullfile(p,[fl{k},'.wav']);
	try,
		audiowrite(fn,s,data(idx(1)).SRATE);
	catch,
		error('unable to write %s',fn);
	end;
	fprintf('wrote %s\n', fn);
end;
