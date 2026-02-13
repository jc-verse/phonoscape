function [g,v] = DelimitGest(s, offs, ht, varargin)
%DELIMITGEST  - identify gesture using velocity extrema
%
%	usage:  [g,v] = DelimitGest(s, offs, ht, ...)
%
% This procedure identifies the following gestural landmarks on signal S nearest to the 
% specified OFFSet using velocity criteria computed with central differencing.  Velocity 
% is either tangential (if S is multidimensional) or absolute magnitude (monodimensional).
%
% Offsets (sample units)
%   MAXC  - closest V minimum to input OFFS (assumed to be maximum constriction)
%   PVEL  - offset of the peak velocity preceding MAXC (closing gesture)
%   PVEL2 - offset of the peak velocity following MAXC (opening gesture)
%   GONS  - gestural onset (THRESH% of the range between the minimum preceding PVEL and PVEL)
%   NONS  - nucleus onset (THRESH% of the range between PVEL and MAXC)
%   NOFFS - nucleus offset (THRESH% of the range between MAXC and following peak velocity PV2)
%   GOFFS - gestural offset (THRESH% of the range between PV2 and following minimum)
%
% Magnitudes (measurement units)
%   PV    - peak tangential velocity (speed at PVEL; dist units/sampling period units)
%   PV2   - peak tangential velocity (speed at PVEL2)
%   DIST  - path integral from GONS to MAXC
%   DIST2 - path integral from MAXC to GOFFS
%   STIFF - stiffness of closing gesture (PV/DIST)
%   STIFF2- stiffness of opening gesture (PV2/DIST2)
%   PD    - peak displacement (Euclidean distance between s(MAXC) and s(GONS); dist units)
%   PD2   - peak displacement (Euclidean distance between s(MAXC) and s(GOFFS); dist units)
% to convert PV to cm/sec with mm dist units and srate in Hz use PV*SRATE/10
%
% signal S should be specified as [nSamps x nComponents]
% search OFFSet (sample units) anchors the search for the nearest gesture
% HT ([head,tail] in sample units) specifies the selection used to constrain MAXC detection 
%   and gestural amplitude validation (if [] the entire signal is used); all fitted labels
%   are also constrained to this interval
%
% returns structure G with fields giving offsets in sample units ([] on error or no gesture found)
% optionally returns velocity signal V
%
% The following 'NAME',VALUE argument pairs are supported (defaults shown as {VALUE}):
%   'THRESH'  - threshold for on/offset detection (percentage):  {.2}
%   'PLOT'    - enable diagnostic plotting:  {'F'} | 'T'
%   'TITLE'	  - plot title string
%
% These parameters override THRESH for specific cases if specified:
%   'THRGONS  - gestural onset threshold (percentage):  {THRESH value}
%   'THRNONS  - nucleus onset threshold (percentage):  {THRESH value}
%   'THRNOFF  - nucleus offset threshold (percentage):  {THRESH value}
%   'THRGOFF  - gestural offset threshold (percentage):  {THRESH value}
%
% Tweak these parameters for use with noisy signals and small peaks associated with plateaux:
%   'FCLP'    - Butterworth LP cutoff:  {.2}
%   'USEFV'   - use filtered vice true velocity for event detection:  {'F'} | 'T'
%   'ONSTHR'  - onset peak must exceed this percentage of max velocity:  {.2}
%   'OFFSTHR' - offset peak must exceed this percentage of max velocity:  {.15}
%
% Any of these parameters may also be specified by defining a variable called DelimitGestParams
% in the base workspace; e.g. 
%   >> DelimitGestParams = {'THRESH',.1,'USEFV','T'} 
%
% SUMMARY OF ALGORITHM:
% 1) tangential velocity (V) computed across all components of S
% 2) filtered velocity (FV) computed using rectangular moving average filter applied symmetrically
% 3) closest minimum to OFFSet identified on FV (initial estimate of MAXC); must lie within current selection
% 4) preceding and following minima to MAXC identified
% 5) amplitude validation:  peak filtered velocities preceding and following MAXC must exceed ONS/OFFSTHR 
%     percentage of max velocity over current selection
% 6) find peak velocities on unfiltered signal bracketing MAXC (PVEL, PVEL2)
% 7) adjust MAXC:  minimum of PVEL:PVEL2 range
% 8) find onsets/offsets using local min/max ranges
%
% see also LP_FINDGEST

% mkt 11/04 from mf_memory
% mkt 05/06 report PVEL2, PV2
% mkt 06/06 mods for THR* override support
% mkt 05/09 mods to constrain MAXC detection and gestural amplitude validation to selection (NYU approach) 
% mkt 10/13 support filter option, small tweaks
% mkt 09/14 include DIST, STIFF
% mkt 12/15 constrain all labels to current selection
% mkt 06/17 return null (placeholder) gesture on nargin<2

% defaults
thresh = .2;
doPlot = 0;
fWin = 5;
useFV = 0;
FcLP = .2;
onsThr = .2;
offsThr = .15;
thrGons = [];
thrNons = [];
thrNoff = [];
thrGoff = [];

% parse args
if nargin < 1,
	eval('help DelimitGest');
	return;
end;
if nargin < 2,	% return null structure
	g = struct('GONS',[],'PVEL',[],'NONS',[],'MAXC',[],'NOFFS',[],'PVEL2',[],'GOFFS',[],...
			'PV',[],'PV2',[],'DIST',[],'DIST2',[],'STIFF',[],'STIFF2',[],'PD',[],'PD2',[]);
	return;
end;
if nargin < 3 || isempty(ht), ht = [1 size(s,1)]; end;
params = [evalin('base','DelimitGestParams','{}') , varargin];
if mod(length(params),2),
	error('DelimitGest argument error:  parameters must be specified in ''NAME'',VALUE format');
end;
titleS = inputname(1);

for ai = 2 : 2 : length(params),
	switch upper(params{ai-1}),
		case 'THRESH', thresh = params{ai};
		case 'PLOT', doPlot = strcmpi(params{ai}(1),'T');
		case 'FWIN', fWin = params{ai};
		case 'USEFV', useFV = strcmpi(params{ai}(1),'T');
		case 'FCLP', FcLP = params{ai};
		case 'ONSTHR', onsThr = params{ai};
		case 'OFFSTHR', offsThr = params{ai};
		case 'TITLE', titleS = params{ai};
		case 'THRGONS', thrGons = params{ai};
		case 'THRNONS', thrNons = params{ai};
		case 'THRNOFF', thrNoff = params{ai};
		case 'THRGOFF', thrGoff = params{ai};
		otherwise, error(sprintf('DelimitGest argument error:  %s', varargin{ai-1}));
	end;
end;
if isempty(thrGons), thrGons = thresh; end;
if isempty(thrNons), thrNons = thresh; end;
if isempty(thrNoff), thrNoff = thresh; end;
if isempty(thrGoff), thrGoff = thresh; end;

g = [];

% compute velocity (central difference)
v = [diff(s(1:2,:)) ; s(3:end,:) - s(1:end-2,:) ; diff(s(end-1:end,:))] ./ 2;
v = sqrt(sum(v.^2,2));
vv = v;
v = v - min(v);
% fv = filtfilt(ones(1,fWin)./fWin,1,FixNaN(v));	% rectangular window moving average filter
[b,a] = butter(3,FcLP);
fv = filtfilt(b,a,FixNaN(v));			% Butterworth LP @ 10%
uv = v;
if useFV, v = fv; end;

% find minima on filtered signal
minima = find(diff([0 ; diff(fv)] > 0) > 0);
[~,n] = min(abs(minima - offs));		% nearest minimum to mouseDn loc
if n == 1 || n == length(minima), return; end;	% need preceding and following minima
MAXC = minima(n);
if MAXC < ht(1) || MAXC > ht(2),		% MAXC outside of selection
	fprintf('DelimitGest:  no MAXC detected within selection\n');
	return;
end;
maxV = max(fv(ht(1):ht(2)));			% velocity magnitude over selection
nn = n - 1;
while nn > 0,							% prune small peaks associated with plateaux
	GONS = minima(nn);
	if abs(max(fv(GONS:MAXC)) - min(fv(GONS:MAXC))) > onsThr*maxV, break; end;
	nn = nn - 1;
end;
if nn < 1 || GONS < ht(1), GONS = ht(1); end;
nn = n + 1;
while nn <= length(minima),
	GOFFS = minima(nn);
	if abs(max(fv(MAXC:GOFFS)) - min(fv(MAXC:GOFFS))) > offsThr*maxV, break; end;
	nn = nn + 1;
end;
if nn > length(minima) || GOFFS > ht(2), GOFFS = ht(2); end;

% now that we have a reliable search range, find maxima on unfiltered signal
[~,PVEL] = max(v(GONS:MAXC));
PVEL = PVEL + GONS - 1;
[~,PVEL2] = max(v(MAXC:GOFFS));
PVEL2 = PVEL2 + MAXC - 1;

% adjust MAXC using unfiltered signal
[~,MAXC] = min(v(PVEL:PVEL2));
MAXC = MAXC + PVEL - 1;

% set onsets using threshold criterion
k = find(v(GONS:PVEL)-v(GONS) > thrGons*(v(PVEL)-v(GONS)));
if isempty(k), fprintf('DelimitGest: failed THRGONS\n'); return; end;
GONS = k(1) + GONS - 1;
k = find(v(PVEL:MAXC)-v(MAXC) > thrNons*(v(PVEL)-v(MAXC)));
if isempty(k), fprintf('DelimitGest: failed THRNONS\n'); return; end;
NONS = k(end) + PVEL - 1;
k = find(v(MAXC:PVEL2)-v(MAXC) > thrNoff*(v(PVEL2)-v(MAXC)));
if isempty(k), fprintf('DelimitGest: failed THRNOFF\n'); return; end;
NOFFS = k(1) + MAXC - 1;
k = find(v(PVEL2:GOFFS)-v(GOFFS) > thrGoff*(v(PVEL2)-v(GOFFS)));
if isempty(k), fprintf('DelimitGest: failed THRGOFF\n'); return; end;
GOFFS = k(end) + PVEL2 - 1;

% find magnitudes
PV = vv(PVEL);									% peak velocity preceding MAXC (mm/sampling period units)
PV2 = vv(PVEL2);								% peak velocity following MAXC
PD = sqrt(sum(diff([s(GONS,:);s(MAXC,:)]).^2));		% peak displacement of closing gesture (mm)
PD2 = sqrt(sum(diff([s(MAXC,:);s(GOFFS,:)]).^2));	% peak displacement of opening gesture (mm)
DIST = sum(sqrt(sum(diff(s(GONS:MAXC,:)).^2,2)));	% path integral closing gesture (mm)
DIST2 = sum(sqrt(sum(diff(s(MAXC:GOFFS,:)).^2,2)));	% path integral closing gesture (mm)
STIFF = PV / DIST;								% stiffness of closing gesture
STIFF2 = PV2 / DIST2;							% stiffness of opening gesture

% bundle results
g = struct('GONS',GONS,'PVEL',PVEL,'NONS',NONS,'MAXC',MAXC,'NOFFS',NOFFS,'PVEL2',PVEL2,'GOFFS',GOFFS,...
			'PV',PV,'PV2',PV2,'DIST',DIST,'DIST2',DIST2,'STIFF',STIFF,'STIFF2',STIFF2,'PD',PD,'PD2',PD2);
if doPlot,
	set(figure, 'name', titleS);
	subplot(211);
	plot(s);
	title(titleS,'interpreter','none');
	set(gca,'xlim',[GONS-5 GOFFS+5],'xtick',[]);
	x = [GONS,PVEL,NONS,MAXC,NOFFS,PVEL2,GOFFS];
	xx = [GONS GONS GOFFS GOFFS GONS];
	yy = [-1 1 1 -1 -1]*PD;
	line(xx,yy,'color','g','lineWidth',2);
	xx = [NONS NONS NOFFS NOFFS NONS];
%	patch(xx,yy,[0 1 0],'eraseMode','xor');
	patch(xx,yy,[0 1 0],'facealpha',.5);
	line([1;1]*x,get(gca,'ylim'),'color','r','linestyle',':');
	pos1 = get(gca,'position');
	subplot(212);
	pos = get(gca,'position');
	pos(4) = pos1(2) - pos(2);
	plot([uv,fv]);
	set(gca,'xlim',[GONS-5 GOFFS+5],'ytick',[],'position',pos);
	ylim = get(gca,'ylim');
	line([1;1]*x,ylim,'color','r','linestyle',':');
	xl = fieldnames(g);
	for n = 1 : 7,
		text(x(n),ylim(2),[' ',xl{n}],'verticalAlignment','top');
	end;
	xlabel('samples');
end;
v = vv;		% unnormalized velocity


%===========================================================================================
% FIXNAN  - replace missing data with linear interpolation between bracketing valid data

function s = FixNaN(s)

missing = find(isnan(s));
if isempty(missing), return; end;
% if length(missing) > .5*length(s),
% 	error('FixNaN:  too many missing values to repair');
% end;

% handle special cases
valid = find(~isnan(s));
if isnan(s(1)),				% beginning
	s(1:valid(1)-1) = s(valid(1));
end;
if isnan(s(end)),			% end
	s(valid(end)+1:end) = s(valid(end));
end;
valid = find(~isnan(s));
if isempty(valid), return; end;

% now bridge gaps
missing = find(isnan(s));
gaps = missing(find(diff([0;missing])>1));
for gi = 1 : length(gaps),
	a = gaps(gi) - 1;
	b = valid(find(valid>gaps(gi)));
	b = b(1);
	k = [a+1 : b-1];
	s(k) = interp1([a;b],s([a;b]),linspace(a,b,length(k)),'pchip');
end;
