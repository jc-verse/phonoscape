function [h,aSig,mu,F0,p,P] = spectra(varargin)
%SPECTRA  - compute and plot spectral cross-section
%
%	usage:	h = spectra(s, t, ...)
%
% Given signal S this procedure computes and plots the spectral cross-section
% at offset time T (msecs) in various ways.
%
% S may be an AUDIO object or a vector of samples followed by a scalar 
% sampling rate (in this case use spectra(s, sr, t, ...))
%
% Additional arguments are optional and specified as 'NAME', VALUE pairs:
%	PREEMP   - signal pre-emphasis; if [] 'adaptive' (default); else 0 <= mu <= 1
%	WSIZE	 - analysis window size (centered on T; default 30 msecs)
%	FRAME	 - FFT points (default is next highest power of 2 containing WSIZE)
%	ORDER	 - LPC order (default srate/1000+4)
%	SOFF	 - SPL reference level (default 20)
%	SEX		 - {'M'} | 'F'; adds 4 coefs to default ORDER, affects F0 heuristics
%	AVGW	 - short-term window size (default 6 msec)
%	OVERLAP	 - short-term window overlap (default 1 msec)
%	NCOEF	 - # cepstral coefficients to retain (default 1/3 detected F0 or 25 SR adjusted)
%	SPEC	 - spectrum type (MAGnitude/POWer; default is 'MAG')
%	DEST 	 - specify an existing axis handle for plotting (default is a new window)
%	SPECLIM	 - display cutoff (Hz; default Nyquist)
%	ANAL	 - specify what to plot, default is {'LPC','DFT'}; available analyses are
%	  LPC  - linear prediction
%	  DFT  - discrete Fourier transform
%	  CEPS - cepstrally smoothed DFT
%	  AVG  - averaged short-term overlapping DFT
%
% Optionally returns a vector of line handles created
%
% see also AVGSPEC, FORMANTS

% mkt 05/01

% hidden return args:  analyzed signal vector ASIG, actual MU, computed F0, computed spectrum, all spectra

%	defaults

mu = [];					% pre-emphasis
wSize = 30;					% analysis window (msecs)
frame = [];					% FFT points
order = [];					% LPC order (use sRate/1000+4)
soff = 20;					% SPL reference level normalization (default 20 microPa; cf. Johnson p53)
avgw = 6;					% short-term window (msecs)
overlap = 1;				% short-term overlap (msecs)
nCoef = [];					% number of cepstral coeficients to retain
spec = 'MAG';				% spectrum type
plotDest = [];				% create new window
specLim = [];				% display cutoff (Hz)
analType = {'LPC','DFT'};	% default analyses
isF = 0;					% true for female subject

%	parse args

if nargin < 2,
	eval('help spectra');
	return;
end;

nargs = nargin;
if isa(varargin{1},'audio'),	% audio object
	signal = varargin{1};
	sr = signal.SRATE;
	signal = double(signal);
elseif isstruct(varargin{1}),	% struct data array (assumes audio is 1st element)
	signal = varargin{1};
	signal = signal(1);
	sr = signal.SRATE;
	signal = signal.SIGNAL;
elseif all([isnumeric(varargin{1}) isnumeric(varargin{2})]),
	signal = varargin{1};		% vector, srate pair
	sr = varargin{2};
	if nargin<3 | max(size(sr)) > 1, 
		error('need scalar sampling rate');
	end;
	varargin = varargin(2:end);
	nargs = nargs - 1;
else,
	error('argument error (signal)');
end;
signal = signal(:)';
t = varargin{2};
if ~isnumeric(t),
	error('argument error (offset)');
end;
for ni = 3 : 2 : nargs,
	switch upper(varargin{ni}),
		case 'PREEMP',	mu = varargin{ni+1};
		case 'WSIZE',	wSize = varargin{ni+1};
		case 'FRAME',	frame = varargin{ni+1};
		case 'ORDER', 	order = varargin{ni+1};
		case 'SOFF', 	soff = varargin{ni+1};
		case 'AVGW', 	avgw = varargin{ni+1};
		case 'OVERLAP',	overlap = varargin{ni+1};
		case 'NCOEF',	nCoef = varargin{ni+1};
		case 'SPEC',	spec = varargin{ni+1};
		case 'DEST', 	plotDest = varargin{ni+1};
		case 'SPECLIM',	specLim = varargin{ni+1};
		case 'ANAL', 	analType = varargin{ni+1}; if ischar(analType), analType = {analType}; end;
		case 'SEX', 	isF = (upper(varargin{ni+1}(1)) == 'F');
		otherwise, error(sprintf('unrecognized option (%s)', varargin{ni}));
	end;
end;

%	get analysis frame

ts = floor(t*sr/1000)+1;				% offset in samples
ns = round(wSize/1000*sr);				% window length in samples
head = ts - round(ns/2);					% head of frame
if head < 1, head = 1; end;
tail = head + ns - 1;						% tail
if tail > length(signal),
	tail = length(signal);
	head = signal - ns + 1;
end;
aSig = signal(head:tail);
if isempty(frame),
	frame = 2^ceil(log(ns)/log(2));		% analysis frame:  next highest power of 2
end;

%	compute F0

F0 = zeros(1,3);
for fi = 1 : 3,							% compute for 3 buffers centered on t
	head = ts - round(ns/2)*(3-fi);
	if head < 1, head = 1; end;
	tail = head + ns - 1;
	if tail > length(signal),
		tail = length(signal);
		head = tail - ns + 1;
	end;
	F0(fi) = ComputeF0(signal(head:tail), sr, isF);
end;
if length(find(F0)) < 2,				% if any two buffers 0
	F0 = 0;									% force to 0
elseif std(F0(find(F0))) > 10,			% if std dev > 10 Hz
	F0 = F0(find(F0));
	if min(F0) < .67*max(F0),				% check for pitch doubling
		if abs(F0(2)-min(F0)) < 10,
			F0 = F0(2);						% use cursor offset if possible
		else,
			F0 = min(F0);
		end;
	else,
		F0 = 0;
	end;
elseif F0(2),							% center result available
	F0 = F0(2);								% cursor-centered result
else,									% otherwise
	F0 = mean(F0(find(F0)));				% mean of non-zero results
end;

% 	pre-emphasize

if isempty(mu), 	% adaptive (cf. Markel & Gray (1976) Linear Prediction of Speech, p216)
	R0 = (aSig * aSig');				% short-time autocorrelation
	R1 = (aSig * [0 aSig(1:end-1)]');
	mu = R1 / R0;						% optimal pre-emphasis coefficient
	if mu < 0, mu = 0; end;				% clip
end;
if mu < 0 | mu > 1,
	error(sprintf('pre-emphasis coefficient error (%g)', mu));
end;
if mu > 0,
	s = filter([1 -mu], 1, aSig);		% s[n] = s[n] - mu*s[n-1]
else,
	s = aSig;
end;

%	plot

if isempty(plotDest),
	fh = colordef('new', 'black');
	set(fh, 'name', sprintf('%s @ %g', inputname(1), round(t*10)/10), 'visible', 'on');
	title(sprintf('WSIZE = %d    FRAME = %d    MU = %g', wSize, frame, round(mu*100)/100));
	uicontrol(fh, ...					% cursor button
				'style', 'pushbutton', ...
				'units', 'characters', ...
				'string', 'Cursor', ...
				'position', [3 0 10 1.5], ...
				'callback', 'disp(''units: Hz, dB'');round(ginput)');
	if F0 > 0,
		uicontrol(fh, ...
				'style', 'text', ...
				'units', 'characters', ...
				'string', sprintf('F0 = %d Hz', F0), ...
				'backgroundColor', get(fh, 'color'), ...
				'foregroundColor', [1 1 1], ...
				'position', [13 0 25 1.2]);
	end;
else,
	axes(plotDest);
end;

%	analyze

h = zeros(1, length(analType));
f = linspace(0, sr/2, frame+1);		% x axis (frequency)
c = 'ygcr';							% colors

for ai = 1 : length(analType),
	ps = strcmp(upper(spec),'POW');		% spectrum type
	switch upper(analType{ai}),
		case 'LPC',
			if isempty(order), 
				order = round(sr/1000) + 4;
				if isF, order = order + 4; end;
			end;
%			[a,g] = lpcg(hanning(ns)' .* s, order);
			sx = hanning(ns) .* s';
			R = flipud(fftfilt(conj(sx),flipud(sx)));	% unbiased autocorrelation estimate
			a = levinson(R, order);						% LPC
			g = sqrt(real(sum((a').*R(1:order+1,:))));	% gain
			p = abs(freqz(g, a, frame+1, sr));
			ps = 0;
			
		case 'DFT',
			p = abs(fft(hanning(ns)' .* s, frame*2));
			if ps, p = p.^2; end;				% power spectrum
			p = p(1:frame+1);					% drop upper reflection
			
		case 'CEPS',
			p = abs(fft(hanning(ns)' .* s, frame*2));
			if ps, p = p.^2; end;				% power spectrum
			p = real(ifft(log(p+eps),frame*2));	% (real) cepstrum
			if isempty(nCoef),
				k = abs(p(10:frame));			% ignore 1st 10 coefs for F0 search
				[v,n] = max(k);
				if isF, cutoff = 300; else, cutoff = 200; end;
				if v/mean(k)>10 & round(sr/(n+9))<cutoff,	% find F0 < cutoff Hz spike if available
					n = n + 9;
					fprintf('Cepstrum-estimated F0 = %d Hz\n', round(sr/n));
					n = round(n/3);				% set cutoff at 1/3 F0
				else,							% set cutoff at 25 coeffs adjusted for SR
					n = round(25 * sr/10000);
				end;
			else,
				n = nCoef;
			end;
			p(n:frame*2-n) = 0;					% rectangular window
			p = abs(fft(p));					% cepstrally smoothed spectrum
			p = exp(p(1:frame+1));				% drop upper reflection
			
		case 'AVG',
			avgw = floor(avgw*sr/1000);			% cvt window size to samples
			avgw = avgw + 1-mod(avgw,2);		% make sure it's odd
			shift = floor(overlap*sr/1000);		% cvt window shift to samples
			avgFrm = 2^ceil(log(avgw)/log(2));	% averaging frame size (avoid excessive zero padding)
			nFrames = round(ns/shift) + 1;		% # frames to average
			w = hamming(avgw)';					% window
			p = zeros(avgFrm+1, nFrames);		% preallocate frame spectra
			sx = [zeros(1,avgw) , s , zeros(1,avgw)];	% pad
			si = ceil(avgw/2);					% sample index
			for fi = 1 : nFrames,				% frame index
				pf = abs(fft(w .* sx(si:si+avgw-1), avgFrm*2));
				if ps, pf = pf.^2; end;			% power spectrum
				p(:,fi) = pf(1:avgFrm+1)';		% drop upper reflection
				si = si + shift;				% shift window
			end;
			p = mean(p,2);						% return average over frames
			p = interp1(linspace(0, sr/2, avgFrm+1), p, f, '*linear');

		otherwise,
			error(sprintf('unrecognized analysis option (%s)', analType{ai}));
	end;
	
	P(:,ai) = p(:);

	if ps, k = 10; else, k = 20; end;
	p = k*log10(p/soff+eps)';				% cvt to normalized dB
	h(ai) = line(f, p, 'color', c(ai));		% plot
	
end;

%	clean up

xlim = [f(1) f(end)];
if ~isempty(specLim), xlim(2) = specLim; end;
set(gca, 'xlim', xlim, 'tag', 'SPECTRA');
xlabel('Hz');
ylabel('dB');
box on;
grid on;

if isempty(plotDest), legend(h, char(analType)); end;

if nargout < 1, clear h; end;

%=============================================================================
%COMPUTEF0  - modified autocorrelation pitch estimator
%
%	usage:  F0 = ComputeF0(s, sr)
%
% Computes pitch estimation based on the filtered error signal autocorrelation 
% sequence to minimize formant interaction (modified autocorrelation analysis)
%
% S is a vector of speech sampled at SR Hz
% returns F0 (Hz)
%
% cf. Markel & Gray (1976) Linear Prediction of Speech, pp. 203-206

function [F0,v,R] = ComputeF0(s, sr, isF);

F0 = 0;
order = 12;
thresh = .4;

% lowpass filter (800 Hz)
s = s(:);
ns = length(s);
[b,a] = cheby2(6,30,1600/sr);
s = filtfilt(b, a, s);

% compute inverse filter
ds = filter([1 -1], 1, s);					% 1st difference
ds = hamming(ns) .* ds;						% window
R = flipud(fftfilt(conj(ds),flipud(ds)));	% autocorrelation vector
a = levinson(R,order);						% inverse filter coefficients

% apply it
fs = filter([1 -a], 1, s);					% inverse filter
fs = hamming(ns) .* fs;						% window
R = flipud(fftfilt(conj(fs),flipud(fs)));	% autocorrelation vector (applied to error)
R = R / R(1);								% normalize

% hunt voicing peak over range from 2.5 ms to half window size - 2.5 ms
ts = round(sr*.0025);						% 2.5 ms in samples
vp = find(diff([0 ; diff(R(ts+1:round(ns/2)-ts))] > 0) < 0) + ts;	% peak indices
v = R(vp);							% normalized values
k = find(v >= thresh);						% peaks exceeding threshold
if isempty(k),
	return;										% none
elseif k < 2,
	vp = vp(k);									% one	
	v = v(k);
else,								% heuristics to avoid pitch doubling/halving
	p = vp / vp;
	p = [0 , p(:,end)'];					% proportional peak periods
	px = linspace(0,1,length(p));			% ideal proportions
	if all(p > px-.02) & all(p < px+.02) & v(2) >= thresh,	% matches period repetition:  voiced
		if isF,
			vp = vp(1);							% female:  1st peak is probable pitch period
		else,
			vp = vp(2);							% male:  2nd peak is probable pitch period
		end;
	else,									% non-ideal pattern, result possibly bogus
		[v,vp] = max(R(ts+1:round(ns/2)-ts));	% use max peak
		vp = vp + ts;
	end;
end;

% convert pitch period to Hz
F0 = round(sr / (vp-1));
