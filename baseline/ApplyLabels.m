function ApplyLabels(data, labels, fName, varargin)
%APPLYLABELS  - extract trajectory values at label offsets from mview data 
%
%	usage:	ApplyLabels(data, labels, fName, ...)
%
% this procedure generates a tab-delimited text file of values at label offsets
% applied to mview compatible array-of-structs data, where
%   DATA   is either a variable or mat filename containing it
%   LABELS is a MELBA or MVIEW generated labels variable 
%   FNAME  is the output filename (data appended to any existing file); def ext '.txt'
%
% optional 'NAME',VALUE parameters supported:
%   DPROC - MELBA/MVIEW data procedure list (default none)
%   ISF   - specify 'T' to improve female F0 heuristics (default 'F')
%   WF0   - F0 window length (default 40 ms)
%   WFMT  - formant computation window length (default 30 ms)
%   WCOG  - COG computation window length (default 50 ms)
%   TLIST - specifies which values to write; defaults are all components of all trajectories
%       tt  - position of trajectory xx; specify components as in e.g. TD13 (default all)
%      vxx  - velocity (central difference; cm/sec); specify components as in e.g. vTD13
%       F0  - fundamental frequency (Hz)
%       Fn  - nth formant (Hz); n == 1,2,3
%       Bn  - nth formant bandwidth (Hz)
%       An  - nth formant amplitude (uncalibrated dB)
%      RMS  - RMS magnitude (uses WFMT window length)
%       ZC  - zero crossing rate (uses WFMT window length)
%      COG  - spectral center of gravity
%
% note that vNN includes all components (including angles, if present); to compute tangential
% velocity on 3D movement components only use vNN123
%
% Examples:
%
% % write values for all components of all trajectories at labelled offsets
% ApplyLabels(data, labels, 'data_vals')
%
% % write values for F0, F1, F2, TT (all), TD (z only) at labelled offsets
% ApplyLabels(data, labels, 'data_vals', 'TLIST',{'F0','F1','F2','TT','TDz'})
%
% % write values for F1 and its bandwidth, TT speed (xyz), lip aperture (via dproc)
% ApplyLabels(data,labels,'data_vals','TLIST',{'F1','B1','vTT123','LA'},'DPROC','mdp_LipAperture')
%
% % write F0 value using 50 ms window and female speaker heuristics
% ApplyLabels(data,labels,'data_vals','TLIST','F0','WF0',50,'ISF','T')

% mkt 11/00
% mkt 01/15 rewritten

% defaults
dproc = [];
isF = 0;
WF0 = 40;
WFMT = 30;
WCOG = 50;
tList = [];

% parse args
if nargin < 3, eval('help ApplyLabels'); return; end
for ai = 2 : 2 : length(varargin),
	switch upper(varargin{ai-1}),
		case 'DPROC', dproc = varargin{ai};
		case 'ISF', isF = strcmpi(varargin{ai}(1),'T');
		case 'WF0', WF0 = varargin{ai};
		case 'WFMT', WFMT = varargin{ai};
		case 'WCOG', WCOG = varargin{ai};
		case 'TLIST', tList = varargin{ai};
		otherwise, error('unrecognized parameter (%s)', varargin{ai-1});
	end	
end

% supported acoustic parameters
aList = {'F0','RMS','ZC','COG','F1','F2','F3','B1','B2','B3','A1','A2','A3'};

% load data
if ischar(data),
	vName = data;
	try,
		data = load(vName);
		data = data.(vName);
	catch,
		error('unable to load data from %s.mat', vName);
	end
else,
	vName = inputname(1);
end

% apply any dprocs
if ~isempty(dproc),
	if ischar(dproc), dproc = {dproc}; end
	for di = 1 : length(dproc),
		dName = dproc{di}; dArgs = {[]};
		if iscell(dName),
			dArgs = dName{2};
			if ischar(dArgs), dArgs = {dArgs}; end;
			dName = dName{1};
		end;
		data = feval(dName, data, dArgs{:}, {[], [], labels});	% palate, pharynx line, labels
	end
end

% construct tList if necessary (all non-audio trajectories; F0, F1,2,3); assume AUDIO first in DATA
dNames = {data.NAME};
if isempty(tList), 
	tList = dNames(2:end);		% AUDIO assumed to be first member of DATA
elseif ~iscell(tList),
	tList = {tList};
end

% map tList against data
tMap = [];
for ti = 1 : length(tList),
	n = tList{ti};
	if n(1) == 'v',
		f = 'VEL'; 			% velocity
		n(1) = [];
	else,
		f = 'MVT';			% mvt
	end
	k = find(strcmp(n,aList));
	if isempty(k),		% expect trajectory name
		q = regexp(n,'(\D+)(\d*)','tokens');
		q = q{1};
		t = q{1}; 
		m = q{2};
		k = find(strcmp(t,dNames));
		if isempty(k), 
			fprintf('%s not found in %s (ignored)\n', t, vName);
			continue;
		end
		if isempty(m),
			c = [1 : size(data(k).SIGNAL,2)];
			m = num2str(c')';
		else,
			c = str2num(m')';
		end;
		if strcmp(f,'VEL'), t = [t,m]; end
	else,				% found acoustic param
		if k < 5,					% one of F0,RMS,ZC,COG
			t = n;
			f = n;
			c = [];
		else,						% Fn, Bn, or An
			t = n(1);
			c = str2num(n(2));		% fmt number
			f = 'FMT';
		end
		k = 1;
	end
	nMap = struct('NAME',t,'INDEX',k,'COMP',c,'FLAG',f);
	if isempty(tMap), tMap = nMap; else, tMap(end+1) = nMap; end
end

% open output file for append
[p,f,e] = fileparts(fName);
if isempty(e), fName = fullfile(p,[f,'.txt']); end
newFile = ~exist(fName, 'file');
fid = fopen(fName, 'at');
if fid < 0, error('unable to open %s for output', fName); end

% write headers for new file
if newFile,
	fprintf(fid,'SOURCE\tNAME\tOFFSET');
	for ti = 1 : length(tMap),
		if strcmp(tMap(ti).FLAG,'VEL'), fprintf(fid,'\tv%s', tMap(ti).NAME); continue; end
		if isempty(tMap(ti).COMP), fprintf(fid,'\t%s', tMap(ti).NAME); continue; end
		for ci = 1 : length(tMap(ti).COMP),
			fprintf(fid,'\t%s%d',tMap(ti).NAME,tMap(ti).COMP(ci));
		end
	end
	fprintf(fid,'\n');
end

% write data
for li = 1 : length(labels),
	fprintf(fid,'%s\t%s\t%.1f', vName, labels(li).NAME, labels(li).OFFSET);
	for ti = 1 : length(tMap),
		d = data(tMap(ti).INDEX);
		idx = floor(labels(li).OFFSET*d.SRATE/1000)+1;		% offset in samples
		switch tMap(ti).FLAG,
			case 'MVT', 		% trajectory
				v = d.SIGNAL(idx,:);
				for ci = 1 : length(tMap(ti).COMP),
					fprintf(fid,'\t%.1f',v(tMap(ti).COMP(ci)));
				end
			case 'VEL',			% velocity
				v = d.SRATE*ComputeVel(d.SIGNAL(:,tMap(ti).COMP))/10;	% cm/sec
				fprintf(fid,'\t%.1f',v(idx));
			case 'FMT',			% formant
				f = NaN(1,3); b = f; a = f;
				[ff,bb,aa] = ComputeFmts1({d.SIGNAL,d.SRATE}, labels(li).OFFSET, WFMT);
				f(1:length(ff)) = ff; b(1:length(bb)) = bb; a(1:length(aa)) = aa;
				switch tMap(ti).NAME,
					case 'F', fprintf(fid,'\t%d', f(tMap(ti).COMP));
					case 'B', fprintf(fid,'\t%d', b(tMap(ti).COMP));
					case 'A', fprintf(fid,'\t%.1f', a(tMap(ti).COMP));
				end
			case 'F0',			% F0
				k = find(strcmp('F0',dNames));
				if isempty(k),		% compute at offset
					v = ComputeF01({d.SIGNAL,d.SRATE}, labels(li).OFFSET, WF0, isF);
				else,				% use pre-computed F0
					d = data(k);
					v = round(d.SIGNAL(floor(labels(li).OFFSET*d.SRATE/1000)+1));
				end;
				fprintf(fid,'\t%d', v);
			case 'COG', 		% COG
				v = cog({d.SIGNAL,d.SRATE}, labels(li).OFFSET, 'WSIZE',WCOG);
				fprintf(fid,'\t%.0f', v);
			case {'RMS','ZC'},	% RMS, ZC
				ht = floor((labels(li).OFFSET+[-WFMT WFMT]/2)*d.SRATE/1000) + 1;
				if ht(1) < 1, ht(1) = 1; end
				if ht(2) > length(d.SIGNAL), ht(2) = length(d.SIGNAL); end
				s = d.SIGNAL(ht(1):ht(2));
				if strcmp(tMap(ti).FLAG,'RMS'),
					fprintf(fid,'\t%.1f', sqrt(mean(s.^2)));		% RMS
				else,
					fprintf(fid, '\t%d', sum(abs(diff(s>=0))));		% ZC
				end
		end
	end
	fprintf(fid,'\n');
end

% clean up
fclose(fid);
fprintf('wrote %s to %s\n', vName, fName);
